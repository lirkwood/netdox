"""
DNS Refresh
***********

Provides a function which links records to their relevant Kubernetes apps and generates some documents about said apps.

This script is used during the refresh process to link DNS records to their apps and to trigger the generation of a publication
which describes all apps running from deployments in the configured Kubernetes clusters.
"""

import json
import logging
from collections import defaultdict
from typing import DefaultDict

from kubernetes import client
from netdox import Network, utils
from netdox.nodes import PlaceholderNode
from netdox.plugins.k8s import initContext
from netdox.plugins.k8s.objs import *

logger = logging.getLogger(__name__)

def getDeployments(apiClient: client.ApiClient, namespace: str='default') -> list[Deployment]:
    """
    Maps deployments in a given namespace to their labels and pod template.

    :param apiClient: The client to use for contacting the API.
    :type apiClient: client.ApiClient
    :param namespace: The namespace to search in, defaults to 'default'.
    :type namespace: str, optional
    :return: A dictionary mapping deployment name to a dictionary of details about it.
    :rtype: dict[str, dict]
    """
    deployments = []
    api = client.AppsV1Api(apiClient)
    allDeps = api.list_namespaced_deployment(namespace)
    for deployment in allDeps.items:
        #TODO investigate if still necessary
        if deployment.spec.template.spec.volumes:
            pvcs = {volume.name: volume.persistent_volume_claim.claim_name for volume in deployment.spec.template.spec.volumes
                    if volume.persistent_volume_claim is not None}
        else:
            pvcs = {}

        containers = []
        for container in deployment.spec.template.spec.containers:
            volumes = []
            if container.volume_mounts:
                for volume in container.volume_mounts:
                    if volume.name in pvcs:
                        volumes.append(MountedVolume(
                            pvc = volume.name,
                            sub_path = volume.sub_path,
                            mount_path = volume.mount_path
                        ))

            containers.append(Container(
                name = container.name,
                image = container.image,
                volumes = volumes
            ))

        deployments.append(Deployment(
            name = deployment.metadata.name,
            labels = deployment.spec.selector.match_labels,
            containers = containers
        ))

    return deployments


def getPodsByLabel(apiClient: client.ApiClient, namespace: str='default') -> dict[int, list[Pod]]:
    """
    Maps the digest of a pod's labels to the name of the pod and its host node.

    :param apiClient: The client to use for contacting the API.
    :type apiClient: client.ApiClient
    :param namespace: The namespace to search in, defaults to 'default'
    :type namespace: str, optional
    :return: A dictionary mapping the sha1 digest of the pod's labels, to a list of dictionaries describing pods with those labels.
    :rtype: dict[str, list[dict[str, str]]]
    """
    podsByLabel: dict[int, list[Pod]] = {}
    api = client.CoreV1Api(apiClient)
    allPods = api.list_namespaced_pod(namespace)
    for pod in allPods.items:
        if pod.metadata.labels and 'pod-template-hash' in pod.metadata.labels:
            _pod = Pod.from_k8s_V1Pod(pod)
            del pod.metadata.labels['pod-template-hash']
            labelHash = hash(json.dumps(pod.metadata.labels, sort_keys=True))
            if labelHash not in podsByLabel:
                podsByLabel[labelHash] = []
            podsByLabel[labelHash].append(_pod)

    return podsByLabel

def getServiceMatchLabels(apiClient: client.ApiClient, namespace: str='default') -> dict[str, dict[str, str]]:
    """
    Maps a service in a given namespace to its match labels.

    :param apiClient: The client to use for contacting the API.
    :type apiClient: client.ApiClient
    :param namespace: The namespace to search in, defaults to 'default'.
    :type namespace: str, optional
    :return: A dictionary mapping the service name to a dictionary of its selectors.
    :rtype: dict[str, dict[str, str]]
    """
    serviceMatchLabels = {}
    api = client.CoreV1Api(apiClient)
    allServices = api.list_namespaced_service(namespace)
    for service in allServices.items:
        serviceMatchLabels[service.metadata.name] = service.spec.selector
    
    return serviceMatchLabels

def getServicePaths(apiClient: client.ApiClient, namespace: str='default') -> dict[str, set]:
    """
    Maps a service in a given namespace to the domains / paths on the domains that will forward requests to it.

    :param apiClient: The client to use for contacting the API.
    :type apiClient: client.ApiClient
    :param namespace: The namespace to search in, defaults to 'default'
    :type namespace: str, optional
    :return: A dictionary mapping service names 
    to the domain paths that resolve to them.
    :rtype: dict[str, set]
    """
    servicePaths = defaultdict(set)
    api = client.NetworkingV1Api(apiClient)
    for ingress in api.list_namespaced_ingress(namespace).items:
        for rule in ingress.spec.rules:
            for path in rule.http.paths:
                servicePaths[path.backend.service.name].add(
                    rule.host + (path.path if path.path else '/'))

    return servicePaths

def getClusterNodeIPs(apiClient: client.ApiClient) -> list[str]:
    """
    Returns a list of the ExternalIP addresses of the cluster nodes.

    :param apiClient: The client to use for contacting the API.
    :type apiClient: client.ApiClient
    :return: List of IPv4 addresses, as strings.
    :rtype: list[str]
    """
    ips: list[str] = []
    api = client.CoreV1Api(apiClient)
    for node in api.list_node().items:
        for addr in node.status.addresses:
            if addr.type == 'ExternalIP':
                ips.append(addr.address)
                continue
    return ips

def getApps(network: Network, context: str, namespace: str='default') -> list[App]:
    """
    Returns a list of apps running from deployments in the specified context/namespace.

    :param context: The kubernetes API context to use.
    :type context: str
    :param namespace: The namespace to search in, defaults to 'default'.
    :type namespace: str, optional
    :return: A dictionary mapping deployment names to some information about the pods that deployment manages.
    :rtype: dict[str]
    """
    #TODO simplify this functions
    cfg = utils.config('k8s')[context]
    rancherBase = f'https://{cfg["host"]}/p/{cfg["clusterId"]}:{cfg["projectId"]}/workloads/{namespace}:'

    apiClient = initContext(context)
    podsByLabel = getPodsByLabel(apiClient, namespace)
    serviceMatchLabels = getServiceMatchLabels(apiClient, namespace)
    servicePaths = getServicePaths(apiClient, namespace)
    cluster = Cluster(context, getClusterNodeIPs(apiClient), 
        location = cfg['location'] if 'location' in cfg else None)

    # map pod names to their ingress paths
    podPaths: DefaultDict[str, set] = defaultdict(set)
    for service, paths in servicePaths.items():
        if service in serviceMatchLabels:
            serviceLabels = hash(json.dumps(serviceMatchLabels[service], sort_keys=True))
            if serviceLabels in podsByLabel:
                for pod in podsByLabel[serviceLabels]:
                    podPaths[pod.name] |= paths
        else:
            logger.warning(f'Domain paths {", ".join(paths)} are being routed to non-existent service {service}'
                +f' (cluster: {context}, namespace: {namespace})')
    
    apps = []
    # construct app by mapping deployment to pods
    deploymentDetails = getDeployments(apiClient, namespace)
    for deployment in deploymentDetails:
        pods = []
        paths = set()
        labelHash = hash(json.dumps(deployment.labels, sort_keys=True))
        if labelHash in podsByLabel:
            for pod in podsByLabel[labelHash]:
                pod.rancher = rancherBase + pod.name
                pods.append(pod)
                
                if pod.name in podPaths:
                    paths |= podPaths[pod.name]

        apps.append(App(
            network = network,
            name = deployment.name,
            pods = pods,
            paths = paths,
            cluster = cluster,
            labels = deployment.labels,
            template = deployment.containers
        ))
    return apps
    

def runner(network: Network) -> None:
    """
    Adds a set of Nodes (called Apps) to the network.

    :param network: The network.
    :type network: Network
    """
    workers = {}
    for context in utils.config('k8s'):
        for app in getApps(network, context):
            for pod in app.pods:
                workers[pod.workerIp] = pod.workerName
    
    for ip, name in workers.items():
        PlaceholderNode(network = network, name = name, ips = [ip])

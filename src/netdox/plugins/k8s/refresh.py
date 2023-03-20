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

def label_match(selector: dict[str, str], labels: dict[str, str]) -> bool:
    """Returns true if the selector labels are all present in the target labels."""
    for key, val in selector.items():
        if key not in labels or labels[key] != val:
            return False
    return True

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
            labels = deployment.metadata.labels,
            selector = deployment.spec.selector.match_labels,
            containers = containers
        ))

    return deployments

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

def get_pods(api_client: client.ApiClient, namespace: str = 'default') -> list[Pod]:
    """Returns all the pods in the namespace."""
    api = client.CoreV1Api(api_client)
    pod_details = api.list_namespaced_pod(namespace)
    pods = []
    for pod in pod_details.items:
        pods.append(Pod.from_k8s_V1Pod(pod))
    return pods

def get_services(api_client: client.ApiClient, namespace: str = 'default') -> list[Service]:
    """Returns all the services in the namespace."""
    ingress_api = client.NetworkingV1Api(api_client)
    ingress_details = ingress_api.list_namespaced_ingress(namespace)
    svc_paths: dict[str, set[str]] = {}
    for ingress in ingress_details.items:
        for rule in ingress.spec.rules:
            for path in rule.http.paths:
                svc_name = path.backend.service.name
                if svc_name not in svc_paths:
                    svc_paths[svc_name] = set()
                svc_paths[svc_name].add(
                    rule.host + (path.path if path.path else '/'))

    svcs = []
    svc_api = client.CoreV1Api(api_client)
    svc_details = svc_api.list_namespaced_service(namespace)
    for svc in svc_details.items:
        svc_name = svc.metadata.name
        svcs.append(Service(
            svc_name,
            svc.metadata.labels,
            svc.spec.selector or {},
            svc_paths[svc_name] if svc_name in svc_paths else set()
        ))
    
    return svcs
    
def get_apps(network: Network, context: str, namespace: str='default') -> list[App]:
    """Creates an App object from every deployment in the namespace."""
    cfg = utils.config('k8s')[context]
    rancherBase = f'https://{cfg["host"]}/p/{cfg["clusterId"]}:{cfg["projectId"]}/workloads/{namespace}:'

    api_client = initContext(context)
    cluster = Cluster(context, getClusterNodeIPs(api_client), 
        location = cfg['location'] if 'location' in cfg else None)
    
    pods = get_pods(api_client, namespace)
    services = get_services(api_client, namespace)
    deployments = getDeployments(api_client, namespace)

    apps = []
    for dep in deployments:
        dep_pods: list[Pod] = []
        for pod in pods:
            if label_match(dep.selector, pod.labels):
                dep_pods.append(pod)
                pods.remove(pod)

        dep_paths = set()
        for svc in services:
            for pod in dep_pods:
                if label_match(svc.selector, pod.labels):
                    dep_paths |= svc.paths

        apps.append(App(
            network,
            dep.name,
            pods = dep_pods,
            paths = dep_paths,
            cluster = cluster,
            labels = dep.labels,
            template = dep.containers
        ))
            
                
    return apps

def runner(network: Network) -> None:
    """
    Adds a set of Nodes (called Apps) to the network.

    :param network: The network.
    :type network: Network
    """
    workers: dict[str, str] = {}
    for context in utils.config('k8s'):
        for app in get_apps(network, context):
            for pod in app.pods:
                if pod.workerIp:
                    workers.setdefault(pod.workerName, pod.workerIp)
    
    for name, ip in workers.items():
        PlaceholderNode(network = network, name = name, ips = [ip])

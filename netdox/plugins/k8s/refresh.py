"""
DNS Refresh
***********

Provides a function which links records to their relevant Kubernetes apps and generates some documents about said apps.

This script is used during the refresh process to link DNS records to their apps and to trigger the generation of a publication
which describes all apps running from deployments in the configured Kubernetes clusters.
"""

import json
from collections import defaultdict

from kubernetes import client

from netdox import utils
from netdox.objs import Domain, Network
from netdox.plugins.k8s import App, initContext


def getDeploymentDetails(namespace: str='default') -> dict[str, dict]:
    """
    Maps deployments in a given namespace to their labels and pod template.

    :param namespace: The namespace to search in, defaults to 'default'.
    :type namespace: str, optional
    :return: A dictionary mapping deployment name to a dictionary of details about it.
    :rtype: dict[str, dict]
    """
    depDetails = {}
    api = client.AppsV1Api(apiClient)
    allDeps = api.list_namespaced_deployment(namespace)
    for deployment in allDeps.items:
        if deployment.spec.template.spec.volumes:
            pvcs = {volume.name: volume.persistent_volume_claim.claim_name for volume in deployment.spec.template.spec.volumes
                    if volume.persistent_volume_claim is not None}
        else:
            pvcs = {}

        containers = {}
        for container in deployment.spec.template.spec.containers:
            volumes = {}
            if container.volume_mounts:
                for volume in container.volume_mounts:
                    if volume.name in pvcs:
                        volumes[pvcs[volume.name]] = {
                            'sub_path': volume.sub_path,
                            'mount_path': volume.mount_path
                        }

            containers[container.name] = {
                'image': container.image,
                'volumes': volumes
            }

        depDetails[deployment.metadata.name] = {
            'labels': deployment.spec.selector.match_labels,
            'template': containers
        }

    return depDetails


def getPodsByLabel(namespace: str='default') -> dict[str, list[dict[str, str]]]:
    """
    Maps the digest of a pod's labels to the name of the pod and its host node.

    :param namespace: The namespace to search in, defaults to 'default'
    :type namespace: str, optional
    :return: A dictionary mapping the sha1 digest of the pod's labels, to a list of dictionaries describing pods with those labels.
    :rtype: dict[str, list[dict[str, str]]]
    """
    podsByLabel = {}
    api = client.CoreV1Api(apiClient)
    allPods = api.list_namespaced_pod(namespace)
    for pod in allPods.items:
        if 'pod-template-hash' in pod.metadata.labels:
            podinfo = {
                'name': pod.metadata.name,
                'workerName': pod.spec.node_name,
                'workerIp': pod.status.host_ip
            }
            del pod.metadata.labels['pod-template-hash']
            labelHash = hash(json.dumps(pod.metadata.labels, sort_keys=True))
            if labelHash not in podsByLabel:
                podsByLabel[labelHash] = []
            podsByLabel[labelHash].append(podinfo)

    return podsByLabel

def getServiceMatchLabels(namespace: str='default') -> dict[str, dict[str, str]]:
    """
    Maps a service in a given namespace to its match labels.

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

def getServicePaths(namespace: str='default') -> dict[str, set]:
    """
    Maps a service in a given namespace to the domains / paths on the domains that will forward requests to it.

    :param namespace: The namespace to search in, defaults to 'default'
    :type namespace: str, optional
    :return: A dictionary mapping service names to the domain paths that resolve to them.
    :rtype: dict[str, set]
    """
    servicePaths = defaultdict(set)
    api = client.ExtensionsV1beta1Api(apiClient)
    allIngress = api.list_namespaced_ingress(namespace)
    for ingress in allIngress.items:
        for rule in ingress.spec.rules:
            for path in rule.http.paths:
                servicePaths[path.backend.service_name].add(rule.host + (path.path if path.path else '/'))

    return servicePaths


def getApps(context: str, namespace: str='default') -> dict[str, dict]:
    """
    Returns a dictionary of apps running from deployments in the specified context/namespace.

    :param context: The kubernetes API context to use.
    :type context: str
    :param namespace: The namespace to search in, defaults to 'default'.
    :type namespace: str, optional
    :return: A dictionary mapping deployment names to some information about the pods that deployment manages.
    :rtype: dict[str]
    """
    global apiClient
    apiClient = initContext(context)
    podsByLabel = getPodsByLabel(namespace)
    serviceMatchLabels = getServiceMatchLabels(namespace)
    serviceDomains = getServicePaths(namespace)

    contextDetails = utils.config()["plugins"]["kubernetes"][context]
    podLinkBase = f'https://{contextDetails["host"]}/p/{contextDetails["clusterId"]}:{contextDetails["projectId"]}/workload/deployment:{namespace}:'

    # map domains to their destination pods
    podPaths = defaultdict(set)
    for service, paths in serviceDomains.items():
        if service in serviceMatchLabels:
            labelHash = hash(json.dumps(serviceMatchLabels[service], sort_keys=True))
            if labelHash in podsByLabel:
                pods = podsByLabel[labelHash]
                for pod in pods:
                    podName = pod['name']
                    podPaths[podName] |= paths
        else:
            print(f'[WARNING][kubernetes] Domain paths {", ".join(paths)} are being routed to non-existent service {service}'
            +f' (cluster: {context}, namespace: {namespace})')
    
    apps = {}
    # construct app by mapping deployment to pods
    deploymentDetails = getDeploymentDetails(namespace)
    for deployment, details in deploymentDetails.items():
        labels = details['labels']
        apps[deployment] = {
            'name': deployment,
            'pods':{},
            'paths': set(),
            'cluster': context,
            'labels': labels,
            'template': details['template']
        }
        app = apps[deployment]

        labelHash = hash(json.dumps(labels, sort_keys=True))
        if labelHash in podsByLabel:
            for pod in podsByLabel[labelHash]:
                podName = pod['name']
                pod['rancher'] = podLinkBase + podName
                app['pods'][podName] = pod
                
                if podName in podPaths:
                    app['paths'] |= podPaths[podName]
    
    return apps
    

def runner(network: Network) -> None:
    """
    Adds a set of Nodes (called Apps) to the network.

    :param network: The network.
    :type network: Network
    """
    auth = utils.config()['plugins']['kubernetes']

    workerApps = {}
    for context in auth:
        apps = getApps(context)
        workerApps[context] = defaultdict(set)
        location = auth[context]['location'] if 'location' in auth[context] else None
        
        for app in apps.values():
            App(network, **app).location = location

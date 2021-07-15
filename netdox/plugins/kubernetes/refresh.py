"""
DNS Refresh
***********

Provides a function which links records to their relevant Kubernetes apps and generates some documents about said apps.

This script is used during the refresh process to link DNS records to their apps and to trigger the generation of a publication
which describes all apps running from deployments in the configured Kubernetes clusters.
"""

from collections import defaultdict
import json

import utils
from networkobjs import Domain, Network
from plugins.kubernetes import initContext, App

from kubernetes import client


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

def getServiceDomains(namespace: str='default') -> dict[str, set]:
    """
    Maps a service in a given namespace to any domains that resolve to it

    :param namespace: The namespace to search in, defaults to 'default'
    :type namespace: str, optional
    :return: A dictionary mapping service names to the domains that resolve to them.
    :rtype: dict[str, set]
    """
    serviceDomains = {}
    api = client.ExtensionsV1beta1Api(apiClient)
    allIngress = api.list_namespaced_ingress(namespace)
    for ingress in allIngress.items:
        for rule in ingress.spec.rules:
            for path in rule.http.paths:
                if path.backend.service_name not in serviceDomains:
                    serviceDomains[path.backend.service_name] = set()
                serviceDomains[path.backend.service_name].add(rule.host)

    return serviceDomains


def getApps(context: str, namespace: str='default') -> dict[str]:
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
    serviceDomains = getServiceDomains(namespace)

    contextDetails = utils.config()["plugins"]["kubernetes"][context]
    podLinkBase = f'https://{contextDetails["host"]}/p/{contextDetails["clusterId"]}:{contextDetails["projectId"]}/workload/deployment:{namespace}:'

    # map domains to their destination pods
    podDomains = {}
    for service, domains in serviceDomains.items():
        if service in serviceMatchLabels:
            labelHash = hash(json.dumps(serviceMatchLabels[service], sort_keys=True))
            if labelHash in podsByLabel:
                pods = podsByLabel[labelHash]
                for pod in pods:
                    podName = pod['name']
                    if podName not in podDomains:
                        podDomains[podName] = set()
                    podDomains[podName] |= domains
        else:
            print(f'[WARNING][kubernetes] Domains {", ".join(domains)} are being routed to non-existent service {service}'
            +f' (cluster: {context}, namespace: {namespace})')
    
    apps = {}
    # construct app by mapping deployment to pods
    deploymentDetails = getDeploymentDetails(namespace)
    for deployment, details in deploymentDetails.items():
        labels = details['labels']
        apps[deployment] = {
            'name': deployment,
            'pods':{},
            'domains': set(),
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
                
                if podName in podDomains:
                    app['domains'] |= podDomains[podName]
    
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
            appnode = App(**app)
            appnode.location = location
            network.add(appnode)

            for domain in appnode.domains:
                if domain not in network.domains:
                    network.domains.add(Domain(domain))

                if not network.domains[domain].location:
                    network.domains[domain].location = location
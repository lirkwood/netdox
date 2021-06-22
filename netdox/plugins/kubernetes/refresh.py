"""
DNS Refresh
***********

Provides a function which links records to their relevant Kubernetes apps and generates some documents about said apps.

This script is used during the refresh process to link DNS records to their apps and to trigger the generation of a publication
which describes all apps running from deployments in the configured Kubernetes clusters.
"""

from plugins.kubernetes import initContext
from kubernetes import client
from plugins import pluginmanager
import json, utils

def getDeploymentDetails(namespace: str='default') -> dict[str, dict[str, str]]:
    """
    Maps deployments in a given namespace to their labels and pod template

    :Args:
        namespace:
            (Optional) The namespace in which to search for deployments

    :Returns:
        A dictionary of all deployments in the namespace/context, their labels and the pod templates they define.
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
    Maps the digest of a pod's labels to the name of the pod and its host node

    :Args:
        namespace:
            (Optional) The namespace in which to search for pods

    :Returns:
        A dictionary mapping pod names to the sha1 digest of their metadata labels
    """
    podsByLabel = {}
    api = client.CoreV1Api(apiClient)
    allPods = api.list_namespaced_pod(namespace)
    for pod in allPods.items:
        if 'pod-template-hash' in pod.metadata.labels:
            podinfo = {
                'name': pod.metadata.name,
                'nodeName': pod.spec.node_name,
            }
            del pod.metadata.labels['pod-template-hash']
            labelHash = hash(json.dumps(pod.metadata.labels, sort_keys=True))
            if labelHash not in podsByLabel:
                podsByLabel[labelHash] = []
            podsByLabel[labelHash].append(podinfo)

    return podsByLabel

def getServiceMatchLabels(namespace: str='default') -> dict[str, dict[str, str]]:
    """
    Maps a service in a given namespace to its match labels

    :Args:
        namespace:
            (Optional) The namespace in which to search for services

    :Returns:
        A dictionary mapping service names to a dictionary of their selector labels
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

    :Args:
        namespace:
            (Optional) The namespace in which to search for services

    :Returns:
        A dictionary mapping service names to a list of domains that resolve to that service
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

def getWorkerAddresses() -> dict[str, dict[str, str]]:
    """
    Maps workers to a specified address type

    :Returns:
        A dictionary mapping worker node names to their addresses (domain name, ipv4, etc.)
    """
    workers = {}
    api = client.CoreV1Api(apiClient)
    allWorkers = api.list_node()
    for worker in allWorkers.items:
        workerName = worker.metadata.name
        workers[workerName] = {}
        for address in worker.status.addresses:
            workers[workerName][address.type] = address.address

    return workers

async def getWorkerVMs(workerAddrs: dict) -> dict[str, str]:
    """
    Talks to the *xenorchestra* plugin in order to map worker names to the VMs they're running in.

    :Args:
        workerAddrs:
            A dictionary like that which is returned by ``getWorkerAddresses``

    :Returns:
        A dictionary mapping worker names to their VM UUID
    """
    from plugins.xenorchestra import fetch as xo
    VMs = await xo.authenticate(xo.fetchType)('VM')
    vmsByIP = {}
    for uuid, vm in VMs.items():
        if '0/ipv4/0' in vm['addresses']:
            ip = vm['addresses']['0/ipv4/0']
            vmsByIP[ip] = uuid

    workerVMs = {}
    for worker, addrTypes in workerAddrs.items():
        if 'InternalIP' in addrTypes:
            addr = addrTypes['InternalIP']
            workerVMs[worker] = vmsByIP[addr]
    return workerVMs


def getApps(context: str, namespace: str='default') -> dict[str]:
    """
    Returns a JSON object of apps in the format expected by apps.xsl

    :Args:
        context:
            The context defined in ``authentication.json`` to perform all actions in.
        namespace:
            (Optional) The namespace to look for resources in (inherited by called functions)

    :Returns:
        A dictionary describing the apps running in this context/namespace
    """
    apps = {}
    global apiClient
    apiClient = initContext(context)
    podsByLabel = getPodsByLabel(namespace)
    serviceMatchLabels = getServiceMatchLabels(namespace)
    serviceDomains = getServiceDomains(namespace)
    workerAddrs = getWorkerAddresses()
    if 'xenorchestra' in pluginmaster:
        from asyncio import run
        workerVMs = run(getWorkerVMs(workerAddrs))
    else:
        workerVMs = {}

    contextDetails = utils.auth()["plugins"]["kubernetes"][context]
    podLinkBase = f'{contextDetails["server"]}/p/{contextDetails["clusterId"]}:{contextDetails["projectId"]}/workload/deployment:{namespace}:'

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
    
    # construct app by mapping deployment to pods
    deploymentDetails = getDeploymentDetails(namespace)
    for deployment, details in deploymentDetails.items():
        labels = details['labels']
        apps[deployment] = {
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
                if pod['nodeName'] in workerVMs:
                    pod['vm'] = workerVMs[pod['nodeName']]
                app['pods'][podName] = pod
                try:
                    app['pods'][podName]['hostip'] = workerAddrs[pod['nodeName']]['InternalIP']
                except KeyError:
                    pass
                if podName in podDomains:
                    app['domains'] |= podDomains[podName]
    
    return apps
    

def runner(forward_dns: utils.DNSSet,*_):
    """
    Links DNSRecords to the Kubernetes apps they resolve to, and generates the k8s_* documents.

    :Args:
        forward_dns:
            A forward DNS set
        _:
            Any object - not used
    """
    auth = utils.auth()['plugins']['kubernetes']
    global pluginmaster
    pluginmaster = pluginmanager()
    allApps = {}
    workers = {}
    for context in auth:
        allApps[context] = getApps(context)
        workers[context] = {}
        for appName, app in allApps[context].items():
            for domain in app['domains']:
                if domain not in forward_dns:
                    forward_dns.add(utils.DNSRecord(domain))
                if not forward_dns[domain].location:
                    if 'location' in auth[context]:
                        forward_dns[domain].location = auth[context]['location']
                forward_dns[domain].link(f'{context}_{appName}', 'Kubernetes')
                
            c_workers = workers[context]
            for _, pod in app['pods'].items():
                if pod['nodeName'] not in c_workers:
                    c_workers[pod['nodeName']] = {'apps':[]}
                    if 'xenorchestra' in pluginmaster:
                        c_workers[pod['nodeName']]['vm'] = pod['vm']
            c_workers[pod['nodeName']]['apps'].append(appName)
    
    with open('plugins/kubernetes/src/apps.json', 'w') as stream:
        stream.write(json.dumps(allApps, indent=2, cls=utils.JSONEncoder))
    with open('plugins/kubernetes/src/workers.json', 'w') as stream:
        stream.write(json.dumps(workers, indent=2, cls=utils.JSONEncoder))
        
    utils.xslt('plugins/kubernetes/apps.xsl', 'plugins/kubernetes/src/apps.xml')
    utils.xslt('plugins/kubernetes/workers.xsl', 'plugins/kubernetes/src/workers.xml')
    utils.xslt('plugins/kubernetes/clusters.xsl', 'plugins/kubernetes/src/workers.xml')
    utils.xslt('plugins/kubernetes/pub.xsl', 'plugins/kubernetes/src/apps.xml', 'out/kubernetes_pub.psml')
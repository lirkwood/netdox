from kubernetes import client, config
import json, utils

## Load config and init client for given context
def initContext(context: str=None):
    config.load_kube_config('plugins/kubernetes/src/kubeconfig', context=context)
    global apiClient
    apiClient = client.ApiClient()


def getDeploymentMatchLabels(namespace: str='default') -> dict[str, dict[str, str]]:
    """
    Maps a service in a given namespace to its match labels
    """
    depMatchLabels = {}
    api = client.AppsV1Api(apiClient)
    allDeps = api.list_namespaced_deployment(namespace)
    for deployment in allDeps.items:
        depMatchLabels[deployment.metadata.name] = deployment.spec.selector.match_labels

    return depMatchLabels

def getPodsByLabel(namespace: str='default') -> dict[str, list[dict[str, str]]]:
    """
    Maps the digest of a pod's labels to some information about it
    """
    podsByLabel = {}
    api = client.CoreV1Api(apiClient)
    allPods = api.list_namespaced_pod(namespace)
    for pod in allPods.items:
        if 'pod-template-hash' in pod.metadata.labels:
            containers = {}
            for container in pod.spec.containers:
                containers[container.name] = container.image
            podinfo = {
                'name': pod.metadata.name,
                'containers': containers,
                'nodeName': pod.spec.node_name,
                'namespace': namespace
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

def getWorkerAddresses():
    """
    Maps workers to a specified address type
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


def getApps(context: str, namespace: str='default') -> dict[str]:
    """
    Returns a JSON object usable by apps.xsl
    """
    apps = {}
    initContext(context)
    podsByLabel = getPodsByLabel(namespace)
    serviceMatchLabels = getServiceMatchLabels(namespace)
    serviceDomains = getServiceDomains(namespace)
    workerAddrs = getWorkerAddresses()

    # map domains to their destination pods
    podDomains = {}
    for service, domains in serviceDomains.items():
        labelHash = hash(json.dumps(serviceMatchLabels[service], sort_keys=True))
        if labelHash in podsByLabel:
            pods = podsByLabel[labelHash]
            for pod in pods:
                podName = pod['name']
                if podName not in podDomains:
                    podDomains[podName] = set()
                podDomains[podName] |= domains
    
    # construct app by mapping deployment to pods
    deploymentMatchLabels = getDeploymentMatchLabels(namespace)
    for deployment, labels in deploymentMatchLabels.items():
        apps[deployment] = {'pods':{},'domains':set()}
        app = apps[deployment]

        labelHash = hash(json.dumps(labels, sort_keys=True))
        if labelHash in podsByLabel:
            for pod in podsByLabel[labelHash]:
                podName = pod['name']
                app['pods'][podName] = pod
                try:
                    app['pods'][podName]['hostip'] = workerAddrs[pod['nodeName']]['InternalIP']
                except KeyError:
                    pass
                if podName in podDomains:
                    app['domains'] |= podDomains[podName]
    
    return apps
    
def main(forward_dns, reverse_dns):
    auth = utils.auth['plugins']['kubernetes']
    allApps = {}
    for context in auth:
        allApps[context] = getApps(context)
        for appName, app in allApps[context].items():
            for domain in app['domains']:
                if domain not in forward_dns:
                    forward_dns[domain] = utils.DNSRecord(domain)
                elif not forward_dns[domain].location:
                    if 'location' in auth[context]:
                        forward_dns[domain].location = auth[context]['location']
                forward_dns[domain].link(appName, 'k8s_app')
    
    with open('plugins/kubernetes/src/apps.json', 'w') as stream:
        stream.write(json.dumps(allApps, indent=2, cls=utils.JSONEncoder))
    workers = {}
    with open('plugins/kubernetes/src/workers.json', 'w') as stream:
        stream.write(json.dumps(workers, indent=2, cls=utils.JSONEncoder))
    utils.xslt('plugins/kubernetes/apps.xsl', 'plugins/kubernetes/src/apps.xml')
    utils.xslt('plugins/kubernetes/workers.xsl', 'plugins/kubernetes/src/workers.xml')
    utils.xslt('plugins/kubernetes/clusters.xsl', 'plugins/kubernetes/src/workers.xml')
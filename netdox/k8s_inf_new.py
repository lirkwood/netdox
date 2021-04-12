import subprocess, utils, json

global selectorLabels
selectorLabels = ('instance', 'app.kubernetes.io/instance', 'app')

# maps service to hostnames it is exposed on
def getIngress():
    serviceDomains = {}
    subprocess.run('./k8s_fetch.sh ingress', shell=True, stdout=subprocess.DEVNULL)
    with open('src/ingress.json', 'r') as stream:
        allIngress = json.load(stream)
        for c in allIngress:
            cluster = allIngress[c]
            serviceDomains[c] = {}
            for ingress in cluster['items']:
                for rule in ingress['spec']['rules']:
                    host = rule['host']
                    for path in rule['http']['paths']:
                        serviceName = path['backend']['serviceName']
                        if serviceName not in serviceDomains[c]:
                            serviceDomains[c][serviceName] = []
                        serviceDomains[c][serviceName].append(host)
    return serviceDomains


# provides shortcut from service to its pod selectors
def getServices():
    serviceSelectors = {}
    subprocess.run('./k8s_fetch.sh services', shell=True, stdout=subprocess.DEVNULL)
    with open('src/services.json', 'r') as stream:
        allServices = json.load(stream)
        for c in allServices:
            cluster = allServices[c]
            serviceSelectors[c] = {}
            for service in cluster['items']:
                serviceName = service['metadata']['name']
                serviceSelectors[c][serviceName] = {}
                if 'selector' in service['spec']:
                    for selector in service['spec']['selector']:
                        serviceSelectors[c][serviceName][selector] = service["spec"]["selector"][selector]
                        # each selector is string in format: 'selector=matchValue'
    return serviceSelectors

    
def getWorkers():
    workers = {}
    subprocess.run('./k8s_fetch.sh nodes "--selector=node-role.kubernetes.io/worker=true"', shell=True, stdout=subprocess.DEVNULL)
    with open('src/nodes.json','r') as workerStream:
        with open('src/vms.json','r') as vmStream:
            allWorkers = json.load(workerStream)
            allVms = json.load(vmStream)
            for c in allWorkers:
                cluster = allWorkers[c]
                workers[c] = {}
                for worker in cluster['items']:
                    for address in worker['status']['addresses']:
                        if address['type'] == 'InternalIP':
                            workerIp = address['address']
                            break
                    
                    if workerIp:
                        for vm in allVms:
                            try:
                                if vm['mainIpAddress'] == workerIp:
                                    workerUuid = vm['uuid']
                            except KeyError:
                                pass

                        workers[c][worker['metadata']['name']] = {
                        "ip": workerIp,
                        "vm": workerUuid,
                        "apps": []
                    }
                    else:
                        print(f'[WARNING][k8s_inf.py] Worker {worker["metadata"]["name"]} has no IP described in nodes.json. Ignoring...')
    return workers


def getPods():
    subprocess.run('./k8s_fetch.sh pods', shell=True, stdout=subprocess.DEVNULL)
    with open('src/pods.json', 'r') as stream:
        allPods = json.load(stream)
        for c in allPods:
            cluster = allPods[c]
            for pod in cluster['items']:
                podInf = {
                    'name': pod['metadata']['name'],
                    'cluster': c,
                    'nodeName': pod['spec']['nodeName'],
                    'hostip': pod['status']['hostIP']
                    }

                # fetch labels
                podInf['labels'] = {}
                for label in pod['metadata']['labels']:
                    podInf['labels'][label] = pod['metadata']['labels'][label]
                
                # fetch containers
                podInf['containers'] = {}
                for container in pod['spec']['containers']:
                    podInf['containers'][container['name']] = container['image']
                
                yield podInf


def service2pod(serviceSelectors):
    servicePods = {}
    for pod in getPods():
        clusterServices = serviceSelectors[pod['cluster']]
        if pod['cluster'] not in servicePods:
            servicePods[pod['cluster']] = {}

        for service in clusterServices:
            match = False
            for selector in clusterServices[service]:
                if selector in pod['labels']:
                    match = True  # If they share a key
                    break
                
            if match:
                try:
                    compareDicts(pod['labels'], clusterServices[service])  # if pod labels and service selectors have no conflicts
                except KeyError:
                    pass
                else:
                    if not service in servicePods:
                        servicePods[pod['cluster']][service] = {}
                        servicePods[pod['cluster']][service][pod['name']] = pod
    return servicePods


def compareDicts(d1, d2):
    intersection = d1.keys() & d2
    if any(d1[shared] != d2[shared] for shared in intersection):
        raise KeyError


def groupServices(serviceSelectors):
    groups = {}
    for c in serviceSelectors:
        groups[c] = {}
        cluster = serviceSelectors[c]
        for service in cluster:
            for selector in selectorLabels:
                if selector in cluster[service]:
                    selectorValue = cluster[service][selector]
                    if selectorValue not in groups:
                        groups[c][selectorValue] = []
                        groups[c][selectorValue].append(service)

                    for _service in cluster:
                        try:
                            if  _service != service and cluster[_service][selector] == selectorValue:
                                groups[c][selectorValue].append(_service)
                        except KeyError:
                            pass
    return groups


def podDomains(servicePods, serviceDomains):
    for c in servicePods:
        for service in servicePods[c]:
            domains = []
            try:
                for domain in serviceDomains[c][service]:
                    domains.append(domain)
            except KeyError:
                pass
            for pod in servicePods[c][service]:
                servicePods[c][service][pod]['domains'] = domains
    return servicePods


def groupPods(servicePods, serviceGroups):
    apps = {}
    for c in servicePods:
        cluster = servicePods[c]
        apps[c] = {}
        for service in cluster:
            for group in serviceGroups[c]:
                if service in serviceGroups[c][group]:
                    if group not in apps[c]:
                        apps[c][group] = {"pods": {}}
                    for pod in cluster[service]:
                        apps[c][group]['pods'][pod] = cluster[service][pod]
    return apps


def podlink(pod):
    if pod['cluster'] == 'sandbox':
        podlinkbase = 'https://rancher.allette.com.au/p/c-4c8qc:p-dtg8s/workloads/default:'
    elif pod['cluster']:
        podlinkbase = 'https://rancher-sy4.allette.com.au/p/c-57mj6:p-b8h5z/workloads/default:'
    else:
        print(f'[WARNING][k8s_inf.py] Unconfigured cluster {pod["cluster"]}. Unable to generate link to rancher.')

    return podlinkbase + pod['name']


def formatApps(apps, workers):
    for c in apps:
        cluster = apps[c]
        for appName in cluster:
            app = cluster[appName]

            domains = set()
            for podName in app['pods']:
                pod = app['pods'][podName]
                pod['rancher'] = podlink(pod)
                pod['vm'] = workers[c][pod['nodeName']]['vm']

                for domain in pod['domains']:
                    domains.add(domain)

                del pod['domains']
                del pod['name']
                del pod['cluster']
            
            app['domains'] = list(domains)
    return apps


def workerApps(apps, workers):
    for c in apps:
        cluster = apps[c]
        for appName in cluster:
            app = cluster[appName]
            for pod in app['pods']:
                workers[c][app['pods'][pod]['nodeName']]['apps'].append(appName)
    
        for worker in workers[c]:
            workers[c][worker]['apps'] = list(dict.fromkeys(workers[c][worker]['apps']))
    return workers


@utils.critical
def main():
    serviceDomains = getIngress()  # map services to domains
    serviceSelectors = getServices()   # map domains to relevant pod labels
    workers = getWorkers()   # returns workername mapped to ip/vm uuid and resident apps
    servicePods = service2pod(serviceSelectors)   # map services to pods
    servicePods = podDomains(servicePods, serviceDomains)   # add domains to pod info
    serviceGroups = groupServices(serviceSelectors)   # groups services based on selectors
    apps = groupPods(servicePods, serviceGroups)    # groups pods based on their service and their service's group
    apps = formatApps(apps, workers)   # adds to/cleans app info and updates workers with their apps
    workers = workerApps(apps, workers)

    with open('src/apps.json','w') as output:
        output.write(json.dumps(apps, indent=2))
    with open('src/workers.json','w') as output:
        output.write(json.dumps(workers, indent=2))


if __name__ == '__main__':
    main()
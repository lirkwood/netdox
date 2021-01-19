from bs4 import BeautifulSoup
import copy
import json
import sys
import csv
import os


def ingress():
    with open('../Sources/ingress.json', 'r') as stream:
        jsondata = json.load(stream)
        idict = {}
        for c in jsondata:  #context either sandbox or production cluster
            context = jsondata[c]
            idict[c] = {}
            for service in context['items']:
                name = service['metadata']['name']
                hosts = []
                for h in service['spec']['rules']:
                    host = h['host'].replace('www.', '').replace('.internal', '')
                    hosts.append(host)

                hosts = list(dict.fromkeys(hosts))  #make unique
                idict[c][name] = hosts  #dict has structure 'service name' : ['host1', 'host2',...] etc
    
    return idict



def service(sdict):
    global links
    ndict = {} #new dictionary
    noingress = {}
    links = {}
    with open('../Sources/services.json', 'r') as stream:
        jsondata = json.load(stream)
        for c in jsondata:
            ndict[c] = {}
            noingress[c] = {}
            context = jsondata[c]
            for service in context['items']:
                name = service['metadata']['name']
                try:
                    if 'app.kubernetes.io/instance' in service['spec']['selector']: #grab app names, some services use older formatting style
                        app = service['spec']['selector']['app.kubernetes.io/instance']
                    elif 'app' in service['spec']['selector']:
                        app = service['spec']['selector']['app']
                    else:
                        app = None
                        print('Found isolated service: {0}. Ignoring...'.format(name))  #if has no link at all
                    try:
                        ndict[c][app] = sdict[c][name]  #dict where deployment is key and associated domains are values
                    except KeyError:
                        print('Found service with no ingress: {0}. Attempting to find related service...'.format(name))
                        noingress[c][name] = app
                except KeyError:
                    print('Found isolated service: {0}. Ignoring...'.format(name))
        for context in noingress:   #sandbox and production
            for service in noingress[context]:  #for each service with no matching ingress
                selector = noingress[context][service]  #value of the service in ndict is its selector; either its deployment or sibling service
                if selector in ndict[context].keys():   #if its sibling service has an entry
                    siblingsdom = ndict[context][selector]  #get its sibling service's domains
                    ndict[context][service] = siblingsdom   #associate unmatched service with sibling's domains
                    print('Service {0} matched on service {1}'.format(service, selector))
                    links[service] = selector   #record links

    return ndict



def pods(sdict):
    global workers
    workers = []
    pdict = {}
    with open('../Sources/pods.json', 'r') as stream:
        jsondata = json.load(stream)
        for c in jsondata:
            pdict[c] = {}
            context = jsondata[c]
            for pod in context['items']:
                labels = pod['metadata']['labels']
                try:
                    if 'app' in labels:
                        appname = labels['app']
                    else:
                        appname = labels['app.kubernetes.io/instance']
                except KeyError:
                    print('Discovered system pod. Ignoring...')
                    appname = None
                podname = pod['metadata']['name']
                if appname:
                    if appname not in pdict[c]:
                        pdict[c][appname] = {}
                        pdict[c][appname]['pods'] = {}
                    pdict[c][appname]['pods'][podname] = {}
                    _pod = pdict[c][appname]['pods'][podname]
                    nodename = pod['spec']['nodeName']
                    hostip = pod['status']['hostIP']
                    workers.append(nodename)
                    try:
                        pdict[c][appname]['nodename'] = nodename
                        pdict[c][appname]['hostip'] = hostip
                        pdict[c][appname]['domains'] = sdict[c][appname]
                        containers = {}
                        for container in pod['spec']['containers']:
                            cname = container['name']
                            image = container['image']
                            containers[cname] = image
                        _pod['containers'] = containers
                            
                    except KeyError:
                        print('Discovered pod with no service {0}. Ignoring...'.format(appname))
    
    return pdict



def mapworkers(pdict):
    global workers
    tmp = {}
    with open('../Sources/domains.csv', 'r') as stream:
        for row in csv.reader(stream):
            if row[0] != 'Kubernetes':
                for worker in workers:
                    if worker in row[1]:
                        tmp[worker] = row[1]
    workers = dict(tmp)

    for context in pdict:
        for domain in pdict[context]:
            pdict[context][domain]['worker'] = workers[pdict[context][domain]['nodename']]
    
    return pdict



def refresh():
    if len(sys.argv) == 2:
        if sys.argv[1] == '-r':
            os.system('pwsh.exe ./get-ingress.ps1')
            os.system('pwsh.exe ./get-services.ps1')
            os.system('pwsh.exe ./get-pods.ps1')
        else:
            print('Invalid argument. Accepted flags are: [-r]')
            exit()
    elif len(sys.argv) > 2:
        print('Too many arguments. Accepted flags are: [-r]')
        exit()
    else:
        return


def podlink(master):
    for context in master:
        for deployment in master[context]:
            dep = master[context][deployment]
            if context == 'sandbox':
                podlinkbase = 'https://rancher.allette.com.au/p/c-4c8qc:p-dtg8s/workloads/default:'
            elif context == 'production':
                podlinkbase = 'https://rancher-sy4.allette.com.au/p/c-57mj6:p-b8h5z/workloads/default:'
            for pod in dep['pods']:
                dep['pods'][pod]['rancher'] = podlinkbase + pod

    return master



def main():
    refresh()
    idict = ingress()
    sdict = service(idict)
    pdict = pods(sdict)
    master = mapworkers(pdict)
    master = podlink(master)
    with open('../Sources/kube.xml', 'w') as out:
        out.write('<root>')
        out.write(json.dumps(master, indent=4))
        out.write('</root>')
    return master



if __name__ == '__main__':
    main()
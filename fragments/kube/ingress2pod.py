from bs4 import BeautifulSoup
import pprint
import json
import csv
import os


def ingress():
    ##### UNCOMMMENT BELOW to get new ingress data #####
    # os.system('pwsh.exe ../Docs/get-ingress.ps1')
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
                    host = h['host'].replace('www.', '')
                    hosts.append(host)

                hosts = list(dict.fromkeys(hosts))  #make unique
                idict[c][name] = hosts  #dict has structure 'service name' : ['host1', 'host2',...] etc
    
    return idict



def service(sdict):
    ##### UNCOMMMENT BELOW to get new service data #####
    # os.system('pwsh.exe ./get-services.ps1')
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
    ##### UNCOMMMENT BELOW to get new pod data #####
    # os.system('pwsh.exe ./get-pods.ps1')
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



def pivot(pdict):   #rearrange dict so domains are the keys and deployments are values
    temp = {}
    for context in pdict:
        temp[context] = {}
        for d in pdict[context]:
            deployment = pdict[context][d]
            try:
                for domain in deployment['domains']:
                    domain = domain.replace('.internal', '')
                    temp[context][domain] = deployment
                    temp[context][domain].pop('domains', None)
            except KeyError:
                pass
    return temp



def podsfrag(d):    #construct kube fragment for posting to rest api
    for context in d:

        if context == 'sandbox':
            podlinkbase = 'https://rancher.allette.com.au/p/c-4c8qc:p-dtg8s/workloads/default:'
        elif context == 'production':
            podlinkbase = 'https://rancher-sy4.allette.com.au/p/c-57mj6:p-b8h5z/workloads/default:'

        for dom in d[context]:
            domain = d[context][dom]
            with open('../Sources/kube_pods-frag-template.xml', 'r') as stream:
                soup = BeautifulSoup(stream, features='xml')    #get all properties as soup objs for multiple uses if necessary
                outsoup = BeautifulSoup('', features='xml')
                frag = outsoup.new_tag('properties-fragment')
                frag['id'] = 'kube_pods'
                outsoup.append(frag)
                for pod in domain['pods']:
                    podsoup = BeautifulSoup(str(soup.find(title='Pod')), features='xml')
                    podlinksoup = BeautifulSoup(str(soup.find(title='Pod on Rancher')), features='xml')
                    frag.append(podsoup)
                    frag.property['value'] = pod
                    frag.append(podlinksoup)
                    frag.find(title='Pod on Rancher')['value'] = podlinkbase + pod
                    _pod = domain['pods'][pod]
                    for container in domain['pods'][pod]['containers']:
                        contsoup = BeautifulSoup(str(soup.find(title='Container')), features='xml')
                        imgsoup = BeautifulSoup(str(soup.find(title='Image ID')), features='xml')
                        frag.append(contsoup)
                        frag.append(imgsoup)
                        frag.find(title='Container')['value'] = container
                        frag.find(title='Image ID')['value'] = _pod['containers'][container]   

                docid = '_nd_' + dom.replace('.', '_')
                filename = docid + ';kube_pods;' #encode fragment name in filename for easier reading
                with open('kube/outgoing/{0}.psml'.format(filename), 'w') as o:
                    o.write(outsoup.prettify())



def workerfrag(master):
    global workers
    for context in master:
        for dom in master[context]:
            domain = master[context][dom]
            with open('../Sources/kube_worker-frag-template.xml') as stream:
                soup = BeautifulSoup(stream, features='xml')
                soup.find(title='Worker Name')['value'] = domain['nodename']
                for xref in soup.find_all('xref'):
                    if xref.parent['name'] == 'worker_ip':
                        xref['docid'] = '_nd_' + domain['hostip'].replace('.', '_')
                    elif xref.parent['name'] == 'worker_host':
                        xref['docid'] = '_nd_' + workers[domain['nodename']].replace('.', '_')

                docid = '_nd_' + dom.replace('.', '_')
                filename = docid + ';kube_worker;'
                with open('kube/outgoing/{0}.psml'.format(filename), 'w') as o:
                    o.write(soup.prettify())



def getworkers():
    global workers
    temp = {}
    with open('../Sources/domains.csv', 'r') as stream:
        for row in csv.reader(stream):
            if row[0] != 'Kubernetes':
                for worker in workers:
                    if worker in row[1]:
                        temp[worker] = row[1]
    workers = temp



def main():
    if not os.path.exists('kube/outgoing'):
        os.mkdir('kube/outgoing')
    idict = ingress()
    sdict = service(idict)
    pdict = pods(sdict)
    master = pivot(pdict)
    with open('Logs/log.json', 'w') as out:
        out.write(json.dumps(master, indent=4))
    podsfrag(master)
    getworkers()
    workerfrag(master)



if __name__ == '__main__':
    main()

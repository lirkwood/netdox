from bs4 import BeautifulSoup
from getpass import getpass
import subprocess
import copy
import json
import sys
import os


def ingress():
    subprocess.run('pwsh.exe ./get-ingress.ps1', check=True, stderr=subprocess.DEVNULL)
    with open('Sources/ingress.json', 'r') as stream:
        jsondata = json.load(stream)
        idict = {}
        for c in jsondata:  #context either sandbox or production cluster
            context = jsondata[c]
            idict[c] = {}
            for ingress in context['items']:
                name = findService(ingress)
                if name:
                    hosts = []
                    for h in ingress['spec']['rules']:
                        host = h['host'].replace('.internal', '')
                        hosts.append(host)

                    hosts = list(dict.fromkeys(hosts))  #make unique
                    idict[c][name] = hosts  #dict has structure 'service name' : ['host1', 'host2',...] etc
                else:
                    print('Found ingress with no destination: '+ ingress['metadata']['name'])
    return idict


def findService(obj):
    if isinstance(obj, dict):
        for item in obj:
            if item == 'serviceName':
                return obj[item]
            else:
                test = findService(obj[item])
                if test: return test
    elif isinstance(obj, list):
        for item in obj:
            test = findService(item)
            if test: return test
    else:
        return None


def service(idict):
    global links
    ndict = {} #new dictionary
    noingress = {}
    links = {}
    subprocess.run('pwsh.exe ./get-services.ps1')
    with open('Sources/services.json', 'r') as stream:
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
                        ndict[c][app] = idict[c][name]  #sdict is dict where ingress is key and associated domains are values
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
    subprocess.run('pwsh.exe ./get-pods.ps1')
    with open('Sources/pods.json', 'r') as stream:
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
                    # print('Discovered system pod. Ignoring...')
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



def mapworkers(pdict, dns):
    global workers
    tmp = {}
    for worker in workers:
        for domain in dns:
            if worker in domain:
                tmp[worker] = domain
    workers = dict(tmp)

    for context in pdict:
        for domain in pdict[context]:
            pdict[context][domain]['worker'] = workers[pdict[context][domain]['nodename']]
    
    return pdict



# def refresh():
#     if len(sys.argv) == 2:
#         if sys.argv[1] == '-r':
#         else:
#             print('Invalid argument. Accepted flags are: [-r]')
#             exit()
#     elif len(sys.argv) > 2:
#         print('Too many arguments. Accepted flags are: [-r]')
#         exit()
#     else:
#         return


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



def worker2app(master):
    with open('sources/workers.json','w') as stream:
        workers = {}
        for context in master:
            workers[context] = {}
            _workers = workers[context]
            for app in master[context]:
                appinf = master[context][app]
                if appinf['nodename'] not in _workers:
                    _workers[appinf['nodename']] = {'ip': appinf['hostip'], 'apps': []}
                if app not in _workers[appinf['nodename']]['apps']:
                    _workers[appinf['nodename']]['apps'].append(app)
        try:
            details = open('Sources/xo.txt','r')
            user = details.readline().strip()
            password = details.readline().strip()
            try:
                subprocess.run('xo-cli --register https://xosy4.allette.com.au '+ user +' '+ password, shell=True, check=True, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                print('Xen Orchestra authentication failed. Clearing bad authentication data...')
                details.close()
                os.remove('Sources/xo.txt')
                return worker2app(master)
            for context in workers:
                for _worker in workers[context]:
                    worker = workers[context][_worker]
                    response = subprocess.check_output('xo-cli --list-objects type=VM mainIpAddress='+ worker['ip'], shell=True)     #xo-cli query goes here
                    vm = json.loads(response)
                    if len(vm) != 1:
                        print('ALERT: Multiple VMs with IP: {0}. Using first returned, name_label={1}'.format(worker['ip'], vm[0]['name_label']))
                    worker['vm'] = vm[0]['uuid']
            details.close()
        except FileNotFoundError:
            if noauth():
                return worker2app(master)
            else:
                pass
        stream.write(json.dumps(workers, indent=2))

def noauth():
	choice = input('***ALERT***\nNo Xen Orchestra authentication details detected. Do you wish to enter them now? (y/n): ')
	if choice == 'y':
		with open('Sources/xo.txt','w') as keys:
			keys.write(getpass('Enter your Xen Orchestra username: '))
			keys.write('\n')
			keys.write(getpass('Enter your Xen Orchestra password: '))
		return True
	elif choice == 'n':
		print('Proceeding without Xen Orchestra data...')
		return False
	else:
		print("Invalid input. Enter 'y' or 'n'.")
		return noauth()


def proceed():
    choice = input('Bad response from Kubernetes; check kubeconfig. Proceed without Kubernetes data? (y/n): ')
    if choice == 'y':
        return True
    elif choice == 'n':
        return False
    else:
        print("Invalid input. Enter 'y' or 'n'.")
        return proceed()


def main(dns):
    try:
        idict = ingress()
    except subprocess.CalledProcessError:
        if proceed():
            return {}
        else:
            quit()
    sdict = service(idict)
    pdict = pods(sdict)
    master = mapworkers(pdict, dns)
    master = podlink(master)
    worker2app(master)
    with open('Sources/apps.json', 'w') as out:
        out.write(json.dumps(master, indent=2))
    return master
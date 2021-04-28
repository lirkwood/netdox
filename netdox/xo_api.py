import subprocess, json, re
import iptools, utils

@utils.critical
def register():
    with open('src/authentication.json', 'r') as stream:
        creds = json.load(stream)['xenorchestra']
    subprocess.check_call(f"xo-cli --register https://{creds['host']} {creds['username']} {creds['password']}", shell=True)


def fetchObjects(dns):
    controllers = set()
    poolHosts = {}
    pools = fetchType('pool')
    for pool in pools:
        poolHosts[pool['uuid']] = []
        controllers.add(pool['master'])
    writeJson(pools, 'pools')

    hosts = fetchType('host')
    for host in hosts:
        if host['uuid'] not in controllers:
            poolHosts[host['$pool']].append(host['uuid'])
            host['subnet'] = iptools.sort(host['address'])
    writeJson(hosts, 'hosts')

    hostVMs = {}
    vms = fetchType('VM')
    for vm in vms:
        vm['name_label'] = re.sub(r'[/\\]','', vm['name_label'])
        
        if vm['$container'] not in hostVMs:
            hostVMs[vm['$container']] = []
        hostVMs[vm['$container']].append(vm['uuid'])
        try:
            vm['subnet'] = iptools.sort(vm['mainIpAddress'])
        except Exception:
            pass

        vm['domains'] = []
        if 'mainIpAddress' in vm:
            for domain in dns:
                if vm['mainIpAddress'] in dns[domain].ips:
                    vm['domains'].append(domain)
        else:
            if vm['power_state'] == 'Running':
                print(f'[WARNING][xo_api.py] VM {vm["name_label"]} has no IP address')
    writeJson(vms, 'vms')
    writeJson(poolHosts, 'devices')
    writeJson(hostVMs, 'residents')

def fetchType(type):
    stdout = subprocess.check_output(f'xo-cli --list-objects type={type}', shell=True)
    jsondata = json.loads(stdout)
    return jsondata

def writeJson(data, type):
    with open(f'src/{type}.json', 'w') as stream:
        stream.write(json.dumps(data, indent=2))
    del data


def createVM(name, desc, template):
    subprocess.check_call(f'xo-cli vm.create name_label={name} name_description={desc} template={template}')
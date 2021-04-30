import requests, json

with open('src/authentication.json','r') as stream:
    icinga_hosts = json.load(stream)['icinga']

def fetchObjects():
    objects = {}
    for icinga in icinga_hosts:
        objects[icinga] = {}

        hosts = fetchType('hosts', icinga)
        services = fetchType('services', icinga)

        hostServices = {}
        for service in services['results']:
            host = service['attrs']['host_name']
            if host not in hostServices:
                hostServices[host] = []
            hostServices[host].append(service['name'])

        for host in hosts['results']:
            name = host['name']
            addr = host['attrs']['address']
            if addr not in objects[icinga]:
                objects[icinga][addr] = {}
            if name in hostServices:
                objects[icinga][addr][name] = hostServices[name]
            else:
                objects[icinga][addr][name] = []
                print(f'[WARNING][icinga_inf.py] Host object {name} has no services.')

    return objects


def fetchType(type, icinga_host):
    auth = icinga_hosts[icinga_host]
    r = requests.get(f'https://{icinga_host}:5665/v1/objects/{type}', auth=(auth["username"], auth["password"]), verify=False)
    jsondata = json.loads(r.text)
    return jsondata
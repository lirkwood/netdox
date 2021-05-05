import requests, json

with open('src/authentication.json','r') as stream:
    icinga_hosts = json.load(stream)['icinga']

def objectsByDomain():
    """
    Returns a dictionary of all hosts and their services, where addr is the key
    """
    manual = {}
    generated = {}
    for icinga in icinga_hosts:
        manual[icinga] = {}
        generated[icinga] = {}

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
            # if generated load template name
            if 'conf.d/hosts/generated/' in host['attrs']['source_location']['path']:
                if addr not in generated[icinga]:
                    generated[icinga][addr] = {"templates": host['attrs']['templates']}
                    if name in hostServices:
                        generated[icinga][addr]['info'] = hostServices[name]
                    # remove top template; should be specific to host
                    if generated[icinga][addr]['templates'][0] == name:
                        del generated[icinga][addr]['templates'][0]
                    else:
                        # remove this
                        print(f'[WARNING][icinga_inf.py] Unexpected behaviour: Top level template has name {generated[icinga][addr][0]} for host {name}')
                else:
                    print(f'[WARNING][icinga_inf.py] Duplicate monitor for {name} in {icinga}')
            # if manually specified load services
            else:
                if addr not in manual[icinga]:
                    manual[icinga][addr] = {}
                if name in hostServices:
                    manual[icinga][addr][name] = hostServices[name]
                else:
                    manual[icinga][addr][name] = []


    return manual, generated


def fetchType(type, icinga_host):
    """
    Returns all instances of a given object type
    """
    auth = icinga_hosts[icinga_host]
    r = requests.get(f'https://{icinga_host}:5665/v1/objects/{type}', auth=(auth["username"], auth["password"]), verify=False)
    jsondata = json.loads(r.text)
    return jsondata


def fetchTemplates(type, icinga_host=None):
    """
    Returns all templates for a given object type
    """
    if not icinga_host:
        icinga_host = list(icinga_hosts)[0]
        
    auth = icinga_hosts[icinga_host]
    r = requests.get(f'https://{icinga_host}:5665/v1/templates/{type}', auth=(auth['username'], auth['password']), verify=False)
    jsondata = json.loads(r.text)
    return jsondata
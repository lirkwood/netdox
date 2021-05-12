import requests, json
import ansible, utils

icinga_hosts = utils.auth['icinga']


def fetchType(type: str, icinga_host: str):
    """
    Returns all instances of a given object type
    """
    auth = icinga_hosts[icinga_host]
    r = requests.get(f'https://{icinga_host}:5665/v1/objects/{type}', auth=(auth["username"], auth["password"]), verify=False)
    jsondata = json.loads(r.text)
    return jsondata

def fetchTemplates(type: str, icinga_host: str):
    """
    Returns all templates for a given object type
    """ 
    auth = icinga_hosts[icinga_host]
    r = requests.get(f'https://{icinga_host}:5665/v1/templates/{type}', auth=(auth['username'], auth['password']), verify=False)
    jsondata = json.loads(r.text)
    return jsondata


def objectsByDomain():
    """
    Returns a dictionary of all hosts and their services, where addr is the key
    """
    global manual, generated
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
            if host['attrs']['groups'] == ['generated']:
                if addr not in generated[icinga]:
                    generated[icinga][addr] = {"templates": host['attrs']['templates'], "services": [host['attrs']['check_command']]}
                    if name in hostServices:
                        generated[icinga][addr]['services'] += hostServices[name]
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


def dnsLookup(dns: utils.dns):
    """
    Add details of any Icinga objects monitoring the host a record resolves to (through name, IP, or CNAME).
    If the monitoring is managed by Netdox, validate current template against the record's role.
    If the validation fails, the template will be updated and the function will return False. The record will not be changed.
    If the record is not currently monitored, one will be applied and the function will return False. The record will not be changed.
    """ 
    manual_monitor = lookupManual(dns)
    for icinga_host in generated:
        if dns.name in generated[icinga_host]:
            if manual_monitor:
                print(f'[WARNING][refresh.py] {dns.name} has manual and generated monitor object. Removing generated object...')
                ansible.icinga_pause(dns.name, icinga = icinga_host)
            else:
                # if template already valid, load service info
                if validateTemplate(dns, icinga_host):
                    if dns.icinga:
                        print(f'[WARNING][refresh.py] {dns.name} has duplicate monitors')
                    dns.icinga = generated[icinga_host][dns.name]['services']
                else:
                    return False

    # if has no monitor, assign one
    if not dns.icinga and dns.location:
        if dns.role and dns.role != 'unmonitored':
            ansible.icinga_set_host(dns.name, dns.location, template = utils.config[dns.role]['template'])
        elif not dns.role:
            ansible.icinga_set_host(dns.name, dns.location)
        else:
            return True
        return False

    return True

def lookupManual(dns: utils.dns):
    global manual
    manual_monitor = False
    for selector in [dns.name] + list(dns.ips):
        for icinga_host in manual:
            # if has a manually created monitor, just load info
            if selector in manual[icinga_host]:
                manual_monitor = True
                if dns.icinga:
                    print(f'[WARNING][refresh.py] {dns.name} has duplicate manual monitors in {icinga_host}')
                dns.icinga = manual[icinga_host][selector]

    return manual_monitor


def validateTemplate(dns: utils.dns, icinga_host: str):
    """
    Validates the template of a dns record against its role, modifies if necessary. Returns True if already valid.
    """
    global generated
    template_name = generated[icinga_host][dns.name]['templates'][0]

    if dns.role:
        if dns.role != 'unmonitored' and dns.role not in template_name:
            print(f'[WARNING][refresh.py] {dns.name} has role {dns.role} but is using Icinga template {template_name}. Replacing...')
            ansible.icinga_set_host(dns.name, icinga = icinga_host, template = utils.config[dns.role]['template'])

        elif dns.role == 'unmonitored':
            print(f'[WARNING][refresh.py] {dns.name} has role {dns.role} but has a generated monitor object. Removing...')
            ansible.icinga_pause(dns.name, icinga = icinga_host)
        
        else:
            return True

    elif not dns.role and template_name != 'generic-host':
        print(f'[WARNING][refresh.py] {dns.name} has no role but is using Icinga template {template_name}. Replacing...')
        ansible.icinga_set_host(dns.name, icinga=icinga_host)

    else:
        return True
    return False
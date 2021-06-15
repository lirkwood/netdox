from plugins.icinga.ssh import set_host, rm_host, reload
from os import rename, mkdir
from shutil import rmtree
from typing import Tuple
import requests, json
import utils

icinga_hosts = utils.auth()['plugins']['icinga']

####################################
# Generic resource fetch functions #
####################################

def fetchType(type: str, icinga_host: str) -> dict:
    """
    Returns all instances of a given object type
    """
    auth = icinga_hosts[icinga_host]
    r = requests.get(f'https://{icinga_host}:5665/v1/objects/{type}', auth=(auth["username"], auth["password"]), verify=False)
    jsondata = json.loads(r.text)
    return jsondata

def fetchTemplates(type: str, icinga_host: str) -> dict:
    """
    Returns all templates for a given object type
    """ 
    auth = icinga_hosts[icinga_host]
    r = requests.get(f'https://{icinga_host}:5665/v1/templates/{type}', auth=(auth['username'], auth['password']), verify=False)
    jsondata = json.loads(r.text)
    return jsondata

#########################
# Main plugin functions #
#########################

def objectsByDomain() -> Tuple[dict, dict]:
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
            hostServices[host].append(service['name'].split('!')[-1])

        for host in hosts['results']:
            name = host['name']
            addr = host['attrs']['address']
            
            if host['attrs']['groups'] == ['generated']:
                group = generated
            else:
                group = manual

            if addr not in group[icinga]:
                group[icinga][addr] = {
                    "templates": host['attrs']['templates'],
                    "services": [host['attrs']['check_command']],
                    "display": name
                }
                if name in hostServices:
                    group[icinga][addr]['services'] += hostServices[name]
                # remove top template; should be specific to host
                if group[icinga][addr]['templates'][0] == name:
                    del group[icinga][addr]['templates'][0]
                else:
                    # remove this
                    print(f'[WARNING][icinga] Unexpected behaviour: Top level template has name {group[icinga][addr][0]} for host {name}')
            else:
                print(f'[WARNING][icinga] Duplicate monitor for {name} in {icinga}')
    return manual, generated


def dnsLookup(dns: utils.DNSRecord) -> bool:
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
                print(f'[WARNING][icinga] {dns.name} has manual and generated monitor object. Removing generated object...')
                rm_host(dns.name, icinga = icinga_host)
            else:
                # if template already valid, load service info
                if validateTemplate(dns, icinga_host):
                    if dns.icinga:
                        print(f'[WARNING][icinga] {dns.name} has duplicate generated monitors')
                    dns.icinga = generated[icinga_host][dns.name]
                else:
                    return False

    # if has no monitor, assign one
    if not dns.icinga and dns.location and 'template' in utils.config[dns.role]:
        if dns.role != 'unmonitored':
            try:
                set_host(dns.name, location = dns.location, template = utils.config[dns.role]['template'])
            except ValueError:
                pass
        else:
            return True
        return False

    return True

def lookupManual(dns: utils.DNSRecord) -> bool:
    """
    Returns bool based on if there is a manually specified monitor on a given DNS name
    """
    global manual
    manual_monitor = False
    for selector in [dns.name] + list(dns.ips):
        for icinga_host in manual:
            # if has a manually created monitor, just load info
            if selector in manual[icinga_host]:
                manual_monitor = True
                if dns.icinga:
                    print(f'[WARNING][icinga] {dns.name} has duplicate manual monitors in {icinga_host}')
                dns.icinga = manual[icinga_host][selector]

    return manual_monitor


def validateTemplate(dns: utils.DNSRecord, icinga_host: str) -> bool:
    """
    Validates the template of a dns record against its role, modifies if necessary. Returns True if already valid.
    """
    global generated
    current = generated[icinga_host][dns.name]['templates'][0]
    try:
        desired = utils.config[dns.role]['template']
    except KeyError:
        return True

    if dns.role != 'unmonitored' and desired != current:
        set_host(dns.name, icinga = icinga_host, template = utils.config[dns.role]['template'])

    elif dns.role == 'unmonitored':
        rm_host(dns.name, icinga = icinga_host)
    
    else:
        return True
    return False


def setServices(dns_set: dict[str, utils.DNSRecord], depth: int=0):
    """
    Iterate over every record in the DNS and set the correct monitors for it, then import the monitoring information into the record.
    """
    if depth <= 1:
        objectsByDomain()
        tmp = {}
        for domain, dns in dns_set.items():
            # create class attr if not exist already
            if not hasattr(dns, 'icinga'):
                setattr(dns, 'icinga', {})
            # search icinga for objects with address == domain (or any ip for that domain)
            if not dnsLookup(dns):
                tmp[domain] = dns

        # reload icinga services to update information coming from api
        for icinga in icinga_hosts:
            reload(icinga=icinga)

        # if some objects had invalid monitors, retest using new data.
        if tmp: setServices(tmp, depth+1)
    else:
        print(f'[WARNING][icinga] Abandoning domains without proper monitor: {dns_set.keys()}')


## Plugin runner
def runner(forward_dns: dict[str, utils.DNSRecord], reverse_dns: dict[str, utils.DNSRecord]):
    setServices(forward_dns)

    # Removes any generated monitors for domains no longer in the DNS
    for icinga, addr_set in generated.items():
        stale = []
        for addr in addr_set:
            if addr not in forward_dns:
                stale.append(addr)
        if stale:
            print(f'[INFO] Found stale monitors: {", ".join(stale)}')
            for addr in stale:
                rm_host(addr, icinga=icinga)
            reload(icinga=icinga)
            
    utils.writeDNS(forward_dns, 'src/dns.json')
    mkdir('out/tmp')
    utils.xslt('plugins/icinga/services.xsl', 'out/DNS', 'out/tmp')
    rmtree('out/DNS')
    rename('out/tmp', 'out/DNS')
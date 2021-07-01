"""
API Functions
*************

Provides functions for interacting with the Icinga API and a class for managing Netdox-generated monitors.
"""
from plugins.icinga.ssh import set_host, rm_host, reload
from os import rename, mkdir
from shutil import rmtree
from typing import Iterable, Tuple
import requests, json
import utils
from networkobjs import Domain, DomainSet, Network, Node

####################################
# Generic resource fetch functions #
####################################

def fetchType(type: str, icinga_host: str) -> dict:
    """
    Returns all instances of a given object type

    :Args:
        type:
            The object type to return
        icinga_host:
            The fqdn of the Icinga instance to query

    :Returns:
        The JSON returned by the server
    """
    try:
        auth = utils.auth()['plugins']['icinga'][icinga_host]
    except KeyError:
        raise ValueError(f'Unrecognised Icinga host: {icinga_host}')
    r = requests.get(f'https://{icinga_host}:5665/v1/objects/{type}', auth=(auth["username"], auth["password"]), verify=False)
    jsondata = json.loads(r.text)
    return jsondata

def fetchTemplates(type: str, icinga_host: str) -> dict:
    """
    Returns all templates for a given object type

    :Args:
        type:
            The object type to return templates for
        icinga_host:
            The fqdn of the Icinga instance to query

    :Returns:
        The JSON returned by the server
    """ 
    try:
        auth = utils.auth()['plugins']['icinga'][icinga_host]
    except KeyError:
        raise ValueError(f'Unrecognised Icinga host: {icinga_host}')
    r = requests.get(f'https://{icinga_host}:5665/v1/templates/{type}', auth=(auth['username'], auth['password']), verify=False)
    jsondata = json.loads(r.text)
    return jsondata

#########################
# Main plugin functions #
#########################

def objectsByDomain(icingas: list[str]) -> Tuple[dict, dict]:
    """
    Returns a map of Icinga host objects to their services

    :Args:
        icingas:
            A list of Icinga instance endpoints to query

    :Returns:
        A dictionary of the services monitoring each address, sorted by Icinga instance
    """
    manual, generated = {}, {}
    for icinga in icingas:
        manual[icinga] = {}

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
                group = manual[icinga]

            if addr not in group:
                group[addr] = {
                    "icinga": icinga,
                    "templates": host['attrs']['templates'],
                    "services": [host['attrs']['check_command']],
                    "display": name
                }
                if name in hostServices:
                    group[addr]['services'] += hostServices[name]
                # remove top template; should be specific to host
                del group[addr]['templates'][0]
            else:
                print(f'[WARNING][icinga] Duplicate monitor for {name} in {icinga}')
    return manual, generated

class MonitorManager:
    """
    Manages the Icinga monitors created by Netdox
    """
    icingas: list[str]
    manual: dict = {}
    generated: dict = {}

    def __init__(self, network: Network) -> None:
        self.icingas = dict(utils.auth()['plugins']['icinga'])
        self.network = network

        self.locationIcingas = {location: None for location in self.network.locator}
        for icinga, details in self.icingas.items():
            icingaLocations = details['locations']
            for location in icingaLocations:
                self.locationIcingas[location] = icinga

        self.refreshMonitorInfo()

    def refreshMonitorInfo(self) -> None:
        """
        Updates the stored monitor details
        """
        self.manual, self.generated = objectsByDomain(self.icingas)

    def manualMonitor(self, domain: Domain) -> bool:
        """
        Tests if a domain or any of its IPs are manually monitored

        :Args:
            dns:
                A DNS record
        
        :Returns:
            True if monitored, False otherwise
        """
        for selector in [domain.name] + list(domain.ips):
            for icinga_host in self.icingas:
                # if has a manually created monitor, just load info
                if selector in self.manual[icinga_host]:
                    return True
        return False

    def validateDomain(self, domain: Domain) -> bool:
        """
        Validates the current monitor on a DNS record. Modifies if necessary.

        :Args:
            record:
                A DNS record to validate the monitoring status of

        :Returns:
            True if the monitor on the record was already valid. False otherwise.
        """
        if (self.manualMonitor(domain) or
            'template' not in utils.config[domain.role] or
            utils.config[domain.role]['template'] == 'None'):
            
            if domain.name in self.generated:
                rm_host(domain.name, icinga = self.generated[domain.name]['icinga'])
                return False

        else:
            if domain.location and self.locationIcingas[domain.location] is not None:
                if domain.name in self.generated:
                    if self.generated[domain.name]['templates'][0] != utils.config[domain.role]['template']:
                        set_host(domain.name, location = domain.location, template = utils.config[domain.role]['template'])
                        return False
                else:
                    set_host(domain.name, location = domain.location, template = utils.config[domain.role]['template'])
                    return False

        return True

    def validateDomains(self, domain_set: Iterable[Domain]) -> list[Domain]:
        """
        Calls validateRecord on each record in a given set, and reloads the relevant Icinga if invalid.

        :Args:
            record_set:
                An iterable of DNSRecords to validate
            
        :Returns:
            A list of DNSRecords which had invalid monitors.
        """
        invalid = []
        needsReload = set()
        for domain in domain_set:
            if self.validateDomain(domain):
                if domain.name in self.generated:
                    setattr(domain, 'icinga', self.generated[domain.name])
                
                else:
                    for icinga in self.icingas:
                        if domain.name in self.manual[icinga]:
                            setattr(domain, 'icinga', self.manual[icinga][domain.name])
            else:
                invalid.append(domain)
                needsReload.add(self.locationIcingas[domain.location])

        for icinga in needsReload:
            reload(icinga = icinga)
        
        return invalid

    def validateNetwork(self) -> None:
        """
        Validates the Icinga monitors of every record in the set, and modifies them to be valid if necessary.

        :Args:
            dns_set:
                A forward DNSSet
        """
        tries = 0
        invalid = list(self.network.domains)
        while tries < 2:
            if tries:
                self.refreshMonitorInfo()
            tries += 1
            invalid = self.validateDomains(invalid)
        
        if invalid:
            print(f'[WARNING][icinga] Unable to resolve invalid monitors for: {", ".join([r.name for r in invalid])}')

    def pruneGenerated(self) -> None:
        """
        Removes all generated monitors whose address is not in the network domain set
        """
        needsReload = set()
        for address, details in self.generated.items():
            if address not in self.network.domains:
                rm_host(address, icinga = details['icinga'])
                needsReload.add(details['icinga'])
        
        for icinga in needsReload:
            reload(icinga = icinga)


## Plugin runner
def runner(network: Network):
    """
    Adds Icinga monitor information to the DNS records in some set.
    If the monitor does not match that of the configured DNS role, this function will attempt to modify it.
    If the monitor continues to appear invalid after 3 attempts it will be abandoned.
    This function will also remove any Netdox-generated monitors on domains which are not in the passed DNS set.

    :Args:
        forward_dns:
            A forward DNS set
        _:
            Any object - not used
    """
    mgr = MonitorManager(network)
    mgr.pruneGenerated()
    mgr.validateNetwork()
            
    # with open('src/forward.json', 'w') as stream:
    #     stream.write(forward_dns.to_json())
    mkdir('out/tmp')
    utils.xslt('plugins/icinga/services.xsl', 'out/domains', 'out/tmp')
    rmtree('out/domains')
    rename('out/tmp', 'out/DNS')
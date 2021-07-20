"""
API Functions
*************

Provides functions for interacting with the Icinga API and a class for managing Netdox-generated monitors.
"""
from bs4 import BeautifulSoup
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
    Returns all instances of a given object type.

    :param type: The type of object to search for.
    :type type: str
    :param icinga_host: The domain name of the Icinga instance to query.
    :type icinga_host: str
    :raises ValueError: If *icinga_host* is not one of the configured values.
    :return: A dictionary returned by the Icinga API.
    :rtype: dict
    """
    try:
        auth = utils.config()['plugins']['icinga'][icinga_host]
    except KeyError:
        raise ValueError(f'Unrecognised Icinga host: {icinga_host}')
    r = requests.get(f'https://{icinga_host}:5665/v1/objects/{type}', auth=(auth["username"], auth["password"]), verify=False)
    jsondata = json.loads(r.text)
    return jsondata

#########################
# Main plugin functions #
#########################

def objectsByDomain(icingas: list[str]) -> Tuple[dict, dict]:
    """
    Returns a tuple of dictionaries containing all host objects known to each Icinga instance in *icingas*.

    The manual dictionary maps the address of each host object not in the ``generated`` host group, to some information about it.
    The generated dictionary maps each instance of icinga to another dictionary, similar to the manual dict, 
    containing the host objects that **do** belong to the ``generated`` host group.  

    :param icingas: A list of domain names of Icinga instances to query.
    :type icingas: list[str]
    :return: A 2-tuple of dictionaries, the manual and generated host objects.
    :rtype: Tuple[dict, dict]
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
                if group is generated:
                    print(f'[WARNING][icinga] Duplicate generated monitor for {name} in {icinga}')
                else:
                    print(f'[WARNING][icinga] Duplicate manual monitor for {name} in {icinga}')
    return manual, generated

class MonitorManager:
    """
    Manages the Icinga monitors created by Netdox
    """
    icingas: list[str]
    manual: dict = {}
    generated: dict = {}

    def __init__(self, network: Network) -> None:
        self.icingas = dict(utils.config()['plugins']['icinga'])
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

        :param domain: A Domain object to test.
        :type domain: Domain
        :return: True if the Domain's name or any members of its *ips* attribute appear as the *address* attribute of a host object,
         in any of the configured Icinga instances. False otherwise.
        :rtype: bool
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

        :param domain: The Domain object to validate.
        :type domain: Domain
        :return: True if the Domain's monitor was already valid. False if it needed to be modified.
        :rtype: bool
        """
        if (self.manualMonitor(domain) or
            'template' not in utils.roles()[domain.role] or
            utils.roles()[domain.role]['template'] == 'None'):
            
            if domain.name in self.generated:
                rm_host(domain.name, icinga = self.generated[domain.name]['icinga'])
                return False

        else:
            if domain.location and self.locationIcingas[domain.location] is not None:
                if domain.name in self.generated:
                    if self.generated[domain.name]['templates'][0] != utils.roles()[domain.role]['template']:
                        set_host(domain.name, location = domain.location, template = utils.roles()[domain.role]['template'])
                        return False
                else:
                    set_host(domain.name, location = domain.location, template = utils.roles()[domain.role]['template'])
                    return False

        return True

    def validateDomainSet(self, domain_set: Iterable[Domain]) -> list[Domain]:
        """
        Calls validateRecord on each record in a given set, and reloads the relevant Icinga if invalid.

        :param domain_set: An iterable object containing Domains.
        :type domain_set: Iterable[Domain]
        :return: A list of Domains that returned **False** when passed to validateDomain
        :rtype: list[Domain]
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
        Validates the Icinga monitors of every Domain in the network, and modifies them to be valid if necessary.
        """
        tries = 0
        invalid = list(self.network.domains)
        while tries < 2:
            if tries:
                self.refreshMonitorInfo()
            tries += 1
            invalid = self.validateDomainSet(invalid)
        
        if invalid:
            print(f'[WARNING][icinga] Unable to resolve invalid monitors for: {", ".join([r.name for r in invalid])}')

    def pruneGenerated(self) -> None:
        """
        Removes all generated monitors whose address is not in the network domain set
        """
        needsReload = set()
        for address, details in self.generated.items():

            if (address not in self.network.domains 
            or (self.network.domains[address].location is not None
                and self.locationIcingas[self.network.domains[address].location] is not None
                and self.locationIcingas[self.network.domains[address].location] != details['icinga'])):    

                rm_host(address, icinga = details['icinga'])
                needsReload.add(details['icinga'])
        
        for icinga in needsReload:
            reload(icinga = icinga)

    def addPSMLFooters(self) -> None:
        """
        Appends a properties-fragment to the psmlFooter of each domain with a monitor.
        """
        for domain in self.network.domains:
            if hasattr(domain, 'icinga'):
                frag = BeautifulSoup(f'''
                <properties-fragment id="icinga">
                    <property name="icinga" title="Icinga Instance" value="{domain.icinga['icinga']}" />
                    <property name="template" title="Monitor Template" value="{domain.icinga['templates'][0]}" />
                </properties-fragment>
                ''', features = 'xml')
                for service in domain.icinga['services']:
                    frag.append(frag.new_tag('property', attrs = {
                        'name': 'service',
                        'title': 'Monitor Service',
                        'value': service
                    }))
                domain.psmlFooter.append(frag)

## Plugin runner
def runner(network: Network):
    """
    Adds Icinga monitor information to the DNS records in some set.
    If the monitor does not match that of the configured DNS role, this function will attempt to modify it.
    If the monitor continues to appear invalid after 3 attempts it will be abandoned.
    This function will also remove any Netdox-generated monitors on domains which are not in the passed DNS set.

    :param network: The network.
    :type network: Network
    """
    mgr = MonitorManager(network)
    mgr.pruneGenerated()
    mgr.validateNetwork()
    mgr.addPSMLFooters()
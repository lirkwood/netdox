"""
API Functions
*************

Provides functions for interacting with the Icinga API and a class for managing Netdox-generated monitors.
"""
import json
from typing import Iterable
from collections import defaultdict

import requests
from bs4 import BeautifulSoup

from netdox import utils
from netdox.objs import Domain, Network
from netdox.plugins.icinga.ssh import reload, rm_host, set_host

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

def fetchMonitors(icinga_host: str) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    """
    Returns a dictionary mapping a unique address to its generated and manually created monitor objects.

    :param icinga_host: The FQDN / IPv4 of the Icinga instance to query.
    :type icinga_host: str
    :return: A 2-tuple of dicts of strings mapped to lists of dictionaries (monitor objects)
    :rtype: tuple[dict[str, list[dict]], dict[str, list[dict]]]
    """
    hosts = fetchType('hosts', icinga_host)
    services = fetchType('services', icinga_host)

    hostServices = {}
    for service in services['results']:
        host = service['attrs']['host_name']
        if host not in hostServices:
            hostServices[host] = []
        hostServices[host].append(service['name'].split('!')[-1])

    generated, manual = defaultdict(list), defaultdict(list)
    for host in hosts['results']:
        # first template is just host name
        host['attrs']['templates'].pop(0)

        # (group is generated) XNOR (group should be generated)
        if host['attrs']['groups'] == ['generated']:
            container = generated
        else:
            container = manual
        container[host['attrs']['address']].append({
            "icinga": icinga_host,
            "address": host['attrs']['address'],
            "templates": host['attrs']['templates'],
            "services": [host['attrs']['check_command']],
            "display": host['name']
        })
    return generated, manual

class MonitorManager:
    """
    Manages the Icinga monitors created by Netdox
    """
    network: Network
    """The network to validate the monitors against."""
    icingas: list[str]
    """List of the FQDN's of the available Icinga instances."""
    locationIcingas: dict[str, str]
    """Maps every location in the network to an Icinga instance FQDN, or `None`."""
    manual: dict
    """Dictionary of the manual monitors."""
    generated: dict
    """Dictionary of the generated monitors."""
    overflow: defaultdict[str, list[dict]]
    """Dictionary to hold extra generated monitors for a given domain."""
    reloadQueue: set[str]
    """A set of Icinga instances that have had their configuration modified."""

    def __init__(self, network: Network) -> None:
        self.network = network
        self.icingas = dict(utils.config()['plugins']['icinga'])

        self.locationIcingas = {location: None for location in self.network.locator}
        for icinga, details in self.icingas.items():
            icingaLocations = details['locations']
            for location in icingaLocations:
                self.locationIcingas[location] = icinga

        self.reloadQueue = set()

        self.refreshMonitorInfo()

    ## Interacting with Icinga instances

    def makeMonitor(self, domain: str, icinga: str, template = 'generic-host') -> None:
        """
        Creates a generated monitor for *domain* in *icinga*.
        Also adds *icinga* to the reload queue.

        :param domain: Address used by the monitor
        :type domain: str
        :param icinga: FQDN of the Icinga instance to create the monitor in.
        :type icinga: str
        """
        set_host(domain, icinga = icinga, template = template)
        self.reloadQueue.add(icinga)

    def removeMonitor(self, domain: str, icinga: str) -> None:
        """
        Removes the generated monitor for *domain* in *icinga*.
        Also adds *icinga* to the reload queue.

        :param domain: Address used by the monitor
        :type domain: str
        :param icinga: FQDN of the Icinga instance to remove the monitor from.
        :type icinga: str
        """
        rm_host(domain, icinga = icinga)
        self.reloadQueue.add(icinga)

    def reload(self) -> None:
        """
        Reloads any Icinga instances that have had their configurations modified.
        """
        for icinga in self.reloadQueue:
            reload(icinga = icinga)
        self.reloadQueue = set()

    ## Data gathering and normalisation

    def refreshMonitorInfo(self) -> None:
        """
        Updates the stored monitor details
        """
        self.generated, self.manual = {}, {}
        self.overflow = defaultdict(list)
        for icinga in self.icingas:
            generated, self.manual[icinga] = fetchMonitors(icinga)
            for domain, monitorlist in generated.items():
                assert len(monitorlist) == 1, f'Multiple monitors on {domain} in {icinga}'
                
                monitor = monitorlist[0]
                if domain not in self.generated:
                    self.generated[domain] = monitor
                else:
                    self.overflow[domain].append(monitor)
        self._resolveOverflow()
    
    def _resolveOverflow(self) -> None:
        """
        Removes extra generated monitors from a domain.
        Will attempt to choose the best instance to keep the monitor
        """
        for domain, monitors in self.overflow.items():
            monitors.append(self.generated[domain])
            location = self.locateDomain(domain)
            if location and self.locationIcingas[location]:
                icinga = self.locationIcingas[location]
            else:
                icinga = self.generated[domain]['icinga']
                print(f'[WARNING][icinga] Unable to meaningfully decide which instance should monitor {domain}; Chose {icinga}')

            for monitor in monitors:
                if monitor['icinga'] != icinga:
                    self.removeMonitor(domain, icinga = monitor['icinga'])
                    monitors.remove(monitor)
            
            if monitors:
                assert len(monitors) == 1
                self.generated[domain] = monitors[0]
            else:
                self.makeMonitor(domain, icinga)
        self.reload()

    ## Monitor validation

    def hasManualMonitor(self, domain: Domain) -> bool:
        """
        Tests if a domain or any of its IPs are manually monitored

        :param domain: A Domain object to test.
        :type domain: Domain
        :return: True if the Domain's name or any members of its *ips* attribute appear as the *address* attribute of a host object,
         in any of the configured Icinga instances. False otherwise.
        :rtype: bool
        """
        for selector in [domain.name] + list(domain.records['A']):
            for icinga_host in self.icingas:
                # if has a manually created monitor, just load info
                if selector in self.manual[icinga_host]:
                    return True
        return False

    def validateDomain(self, domain: Domain) -> bool:
        """
        Validates the current monitor on a domain. Modifies if necessary.

        :param domain: The Domain object to validate.
        :type domain: Domain
        :return: True if the Domain's monitor was already valid. False if it needed to be modified.
        :rtype: bool
        """
        if (self.hasManualMonitor(domain) or
            'template' not in utils.roles()[domain.role] or
            utils.roles()[domain.role]['template'] == 'None'):
            
            # if manual and generated monitor
            if domain.name in self.generated:
                self.removeMonitor(domain.name, icinga = self.generated[domain.name]['icinga'])
                return False

        else:
            location = self.locateDomain(domain.name)
            icinga = self.locationIcingas[location] if location in self.locationIcingas else None
            if icinga:
                if domain.name in self.generated:
                    # if location wrong
                    if self.generated[domain.name]['icinga'] != icinga:
                        self.removeMonitor(domain.name, icinga = self.generated[domain.name]['icinga'])
                        self.makeMonitor(domain.name, icinga, utils.roles()[domain.role]['template'])
                        return False
                    # if template wrong
                    elif self.generated[domain.name]['templates'][0] != utils.roles()[domain.role]['template']:
                        self.makeMonitor(domain.name, icinga, utils.roles()[domain.role]['template'])
                        return False
                # if no monitor
                else:
                    self.makeMonitor(domain.name, icinga, utils.roles()[domain.role]['template'])
                    return False

        return True

    def validateDomainSet(self, domain_set: Iterable[Domain]) -> list[Domain]:
        """
        Returns a list of domains that previously had invalid monitors on them,
        so that the Icinga instances can be reloaded and validated again.

        :param domain_set: An iterable object containing Domains.
        :type domain_set: Iterable[Domain]
        :return: A list of Domains that returned **False** when passed to validateDomain
        :rtype: list[Domain]
        """
        invalid = []
        for domain in domain_set:
            if self.validateDomain(domain):
                if domain.name in self.generated:
                    domain.icinga = self.generated[domain.name]
                else:
                    for icinga in self.icingas:
                        if domain.name in self.manual[icinga]:
                            domain.icinga = self.manual[icinga][domain.name][0]
            else:
                invalid.append(domain)
        
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
            self.reload()
        
        if invalid:
            print(f'[WARNING][icinga] Unable to resolve invalid monitors for:\n\t', \
                ",\n\t".join([r.name for r in invalid]))

    def pruneGenerated(self) -> None:
        """
        Removes all generated monitors whose address is not in the network domain set
        """
        for address, details in self.generated.items():
            if address not in self.network.domains:
                self.removeMonitor(address, icinga = details['icinga'])
        self.reload()

    ## Miscellaneous

    def locateDomain(self, domain: str) -> str:
        """
        Guesses the best location to attribute to a domain name.
        Returns None if no location can be found.

        Checks in the network if the domain has a location through its node,
        and if not attempts to locate based on it's A records.

        :param domain: A FQDN to locate
        :type domain: str
        :return: The location of the domain, or None
        :rtype: str
        """
        if domain in self.network.domains:
            if self.network.domains[domain].node:
                return self.network.domains[domain].node.location
            else:
                return self.network.locator.locate(
                    self.network.domains[domain].records['A']
                )
        return None

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
                    frag.find(id='icinga').append(frag.new_tag('property', attrs = {
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
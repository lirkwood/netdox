import logging
from collections import defaultdict
from typing import Iterable, Optional

from bs4 import BeautifulSoup
from netdox import Domain, Network, utils
from netdox.plugins.icinga.api import (TEMPLATE_ATTR, createHost,
                                       fetchMonitors, removeHost,
                                       updateHostTemplate)

logger = logging.getLogger(__name__)

class MonitorManager:
    """
    Manages the Icinga monitors created by Netdox
    """
    network: Network
    """The network to validate the monitors against."""
    icingas: list[str]
    """List of the FQDN's of the available Icinga instances."""
    locationIcingas: dict[str, str]
    """Maps every location in the network to an Icinga instance FQDN, or ``None``."""
    manual: dict
    """Dictionary of the manual monitors."""
    generated: dict
    """Dictionary of the generated monitors."""
    overflow: defaultdict[str, list[dict]]
    """Dictionary to hold extra generated monitors for a given domain."""

    def __init__(self, network: Network) -> None:
        self.network = network
        icinga_details = dict(utils.config('icinga'))

        self.icingas = list(icinga_details)
        self.locationIcingas = dict.fromkeys(self.network.locator)
        for icinga, details in icinga_details.items():
            icingaLocations = details['locations']
            for location in icingaLocations:
                self.locationIcingas[location] = icinga

        self.manual, self.generated = {}, {}

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
                logger.warning(f'Unable to meaningfully decide which instance should monitor {domain}; Chose {icinga}')

            for monitor in monitors:
                if monitor['icinga'] != icinga:
                    removeHost(icinga, domain)
                    monitors.remove(monitor)
            
            if monitors:
                assert len(monitors) == 1
                self.generated[domain] = monitors[0]
            else:
                createHost(icinga, domain)

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
        for selector in domain.domains:
            for icinga_host in self.icingas:
                # if has a manually created monitor, just load info
                if selector in self.manual[icinga_host]:
                    return True
        return False

    def requestsMonitor(self, domain: Domain) -> bool:
        return bool(
            domain.getAttr(TEMPLATE_ATTR) and domain.getAttr(TEMPLATE_ATTR) != 'None'
            and domain.name not in self.icingas
        )

    def validateDomain(self, domain: Domain) -> bool:
        """
        Validates the current monitor on a domain. Modifies if necessary.

        :param domain: The Domain object to validate.
        :type domain: Domain
        :return: True if the Domain's monitor was already valid. False if it needed to be modified.
        :rtype: bool
        """
        manual_monitor = self.hasManualMonitor(domain)
        requests_monitor = self.requestsMonitor(domain)
        
        if (manual_monitor or not requests_monitor) and domain.name in self.generated:
            removeHost(self.generated[domain.name]['icinga'], domain.name)
            return False

        elif requests_monitor and not manual_monitor:
            location = self.locateDomain(domain.name)
            icinga = self.locationIcingas[location] if location in self.locationIcingas else None
            if icinga:
                if domain.name in self.generated:
                    # if location wrong
                    if self.generated[domain.name]['icinga'] != icinga:
                        removeHost(self.generated[domain.name]['icinga'], domain.name)
                        createHost(icinga, domain.name, domain.getAttr(TEMPLATE_ATTR)) # type: ignore
                        return False
                    # if template wrong
                    elif self.generated[domain.name]['templates'][0] != domain.getAttr(TEMPLATE_ATTR):
                        updateHostTemplate(icinga, domain.name, domain.getAttr(TEMPLATE_ATTR)) # type: ignore
                        return False
                # if no monitor
                else:
                    createHost(icinga, domain.name, domain.getAttr(TEMPLATE_ATTR)) # type: ignore # TODO find mypy fix
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
                    setattr(domain, 'icinga', self.generated[domain.name])
                else:
                    for icinga in self.icingas:
                        if domain.name in self.manual[icinga]:
                            setattr(domain, 'icinga', self.manual[icinga][domain.name][0])
            else:
                invalid.append(domain)
        
        return invalid

    def validateNetwork(self) -> None:
        """
        Validates the Icinga monitors of every Domain in the network, and modifies them to be valid if necessary.
        """
        self.refreshMonitorInfo()
        self.pruneGenerated()
        invalid = self.validateDomainSet(self.network.domains)

        if invalid:
            self.refreshMonitorInfo()
            invalid = self.validateDomainSet(invalid)

        if invalid:
            logger.warning("Unable to resolve invalid monitors for: '" +
                "', '".join([ domain.name for domain in invalid ]) + "'")

    def pruneGenerated(self) -> None:
        """
        Removes all generated monitors whose address is not in the network domain set
        """
        for address, details in self.generated.items():
            if address not in self.network.domains:
                removeHost(details['icinga'], address)

    ## Miscellaneous

    def locateDomain(self, domain: str) -> Optional[str]:
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
            node = self.network.domains[domain].node
            if node: return node.location
            else:
                return self.network.locator.locate(
                    self.network.domains[domain].records.A.names
                )
        return None

    def addPSMLFooters(self) -> None:
        """
        Appends a properties-fragment to the psmlFooter of each domain with a monitor.
        """
        for domain in self.network.domains:
            icinga_details = getattr(domain, 'icinga', None)
            if icinga_details:
                frag = BeautifulSoup(f'''
                <properties-fragment id="icinga">
                    <property name="icinga" title="Icinga Instance" value="{icinga_details['icinga']}" />
                    <property name="template" title="Monitor Template" value="{icinga_details['templates'][0]}" />
                </properties-fragment>
                ''', features = 'xml')
                for service in icinga_details['services']:
                    frag.find(id='icinga').append(frag.new_tag('property', attrs = {
                        'name': 'service',
                        'title': 'Monitor Service',
                        'value': service
                    }))
                domain.psmlFooter.append(frag)

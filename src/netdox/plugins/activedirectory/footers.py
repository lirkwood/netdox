import logging

from bs4 import BeautifulSoup
from pypsrp.powershell import PowerShell, RunspacePool
from pypsrp.wsman import WSMan

from netdox import utils
from netdox import Domain, Network
from netdox.nodes import PlaceholderNode
from netdox.psml import PropertiesFragment, Property

logger = logging.getLogger(__name__)

def addFooters(network: Network) -> None:
    """
    Adds a fragment of information from ActiveDirectory Users and Computers to the relevant node,
    if it exists.

    :param network: The network.
    :type network: Network
    """
    wsman = WSMan(**utils.config('activedirectory'), ssl = False)
    with wsman, RunspacePool(wsman) as pool:
        domain = PowerShell(pool).add_cmdlet('Get-ADDomain').add_parameter('Current','LoggedOnUser').invoke()[0]
        zone = domain.adapted_properties['DNSRoot']
        ps = PowerShell(pool).add_cmdlet('Get-ADComputer').add_parameter('Filter', '*')\
            .add_parameter('Properties', ['IPv4Address', 'Description', 'MemberOf'])

        for computer in ps.invoke():
            properties: dict = computer.adapted_properties

            groups = []
            groupsoup = BeautifulSoup(properties['MemberOf'].property_sets[0], 'xml')
            for group in groupsoup('S'):
                groups.append(group.string.split(',')[0].replace('CN=',''))

            frag = PropertiesFragment('activedirectory', [
                Property(
                    'distinguishedname', 
                    properties['DistinguishedName'], 
                    'Distinguished Name'),
                Property(
                    'desc', 
                    properties['Description'] if properties['Description'] else '—', 
                    'Description'),
                Property(
                    'groups', 
                    groups, 
                    'Groups')
            ])

            domains = []
            if properties['DNSHostName'] and properties['DNSHostName'] not in network.domains:
                try:
                    Domain(network, properties['DNSHostName'], zone = zone)
                    domains.append(properties['DNSHostName'])
                except ValueError:
                    logger.error(f'Invalid domain name discovered on node: {properties["DNSHostName"]}')
            
            name = None
            for item in properties['DistinguishedName'].split(','):
                if item.startswith('CN=') and len(item) > 3:
                    name = item[3:]
                    break
                
            try:
                ips = [properties['IPv4Address']] if properties['IPv4Address'] else []
                for dns in domains + ips:
                    node = network.find_dns(dns).node
                    if node is not None:
                        node.psmlFooter.insert(frag)
            except AssertionError:
                logger.warning(f'Computer \'{properties["Name"]}\' has addresses that resolve to different nodes.'\
                    + ' This can be caused by ambiguous DNS records or misconfiguration in ActiveDirectory.')


if __name__ == '__main__':
    addFooters(Network.from_dump())

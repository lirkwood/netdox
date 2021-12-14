import logging

from bs4 import BeautifulSoup
from pypsrp.powershell import PowerShell, RunspacePool
from pypsrp.wsman import WSMan

from netdox import utils
from netdox import Domain, Network
from netdox.nodes import PlaceholderNode

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

            frag = BeautifulSoup(f'''
            <properties-fragment id="activedirectory">
                <property name="distinguishedname" title="Distinguished Name" value="{properties['DistinguishedName']}" />
                
                <property name="desc" title="Description" 
                    value="{properties['Description'] if properties['Description'] else '—'}" />

                <property name="groups" title="Groups" multiple="true">
                    {''.join(['<value>'+ g +'</value>' for g in groups])}
                </property>
            </properties-fragment>''', 'xml')

            if properties['DNSHostName'] and properties['DNSHostName'] not in network.domains:
                Domain(network, properties['DNSHostName'], zone = zone)

            try:
                identity = PlaceholderNode(
                    network = network,
                    name = properties['Name'],
                    domains = [properties['DNSHostName']] if properties['DNSHostName'] else [],
                    ips = [properties['IPv4Address']] if properties['IPv4Address'] else [],
                ).identity

                network.nodes[identity].psmlFooter.append(frag)
            except AssertionError:
                logger.warning(f'Computer \'{properties["Name"]}\' has addresses that resolve to different nodes.'\
                    + ' This can be caused by ambiguous DNS records or misconfiguration in ActiveDirectory.')


if __name__ == '__main__':
    addFooters(Network.fromDump())

from bs4 import BeautifulSoup
from pypsrp.powershell import PowerShell, RunspacePool
from pypsrp.wsman import WSMan

from netdox import utils
from netdox.objs import Network, Domain

def addFooters(network: Network) -> None:
    """
    Adds a fragment of information from ActiveDirectory Users and Computers to the relevant node,
    if it exists.

    :param network: The network.
    :type network: Network
    """
    wsman = WSMan(**utils.config()['plugins']['activedirectory'], ssl = False)
    with wsman, RunspacePool(wsman) as pool:
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
                <property name="distinguishedname" title="Distinguished Name" value="{properties['DistinguishedName']}" />"
                
                <property name="desc" title="Description" 
                    value="{properties['Description'] if properties['Description'] else '—'}" />

                <property name="groups" title="Groups" multiple="True">
                    {''.join(['<value>'+ g +'</value>' for g in groups])}
                </property>
            </properties-fragment>''', 'xml')

            if properties['DNSHostName'] and properties['DNSHostName'] not in network.domains:
                Domain(network, properties['DNSHostName'])

            if properties['DNSHostName'] and network.domains[properties['DNSHostName']].node:
                network.domains[properties['DNSHostName']].node.psmlFooter.append(frag)
            if properties['IPv4Address'] and network.ips[properties['IPv4Address']].node:
                network.ips[properties['IPv4Address']].node.psmlFooter.append(frag)

if __name__ == '__main__':
    addFooters(Network.fromDump())

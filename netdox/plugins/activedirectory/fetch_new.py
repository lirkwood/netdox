import utils
import re
from networkobjs import Network
from pypsrp.powershell import PowerShell, RunspacePool
from pypsrp.wsman import WSMan
from pprint import pprint

def runner(network: Network) -> None:
    conf = utils.config()['plugins']['activedirectory']
    wsman = WSMan(
        server = conf['host'], 
        username = conf['username'], 
        password = conf['password'],
        ssl = False
    )
    with wsman, RunspacePool(wsman) as pool:
        ps = PowerShell(pool)
        ps.add_cmdlet('Get-DnsServerZone')
        zones = list(ps.invoke())

        ps = PowerShell(pool)
        for zone in zones:

            ps.add_cmdlet('Get-DnsServerResourceRecord')\
                .add_parameter('ZoneName', zone.adapted_properties['ZoneName'])\
                .add_parameter('RRType', 'A')
            ps.add_statement()
                
            ps.add_cmdlet('Get-DnsServerResourceRecord')\
                .add_parameter('ZoneName', zone.adapted_properties['ZoneName'])\
                .add_parameter('RRType', 'CNAME')
            ps.add_statement()
                
            ps.add_cmdlet('Get-DnsServerResourceRecord')\
                .add_parameter('ZoneName', zone.adapted_properties['ZoneName'])\
                .add_parameter('RRType', 'PTR')
            ps.add_statement()

        records = ps.invoke()
        for record in records:
            print(fqdnFromDN(record.adapted_properties['DistinguishedName']))

dc_pattern = re.compile(r'DC\s*=\s*(?P<dc>.*)$', re.IGNORECASE)

def fqdnFromDN(distinguished_name: str) -> str:
    name = []
    for statement in distinguished_name.split(','):
        match = re.match(dc_pattern, statement)
        if match:
            if match['dc'] == '*':
                name.append('_wildcard_')
            elif match['dc'] != '@':
                name.append(match['dc'])
            
        else:        
            return '.'.join(name).lower()

if __name__ == '__main__':
    runner('')
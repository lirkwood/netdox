import re
from pprint import pprint
from typing import Iterable

import utils
from networkobjs import Domain, IPv4Address, Network
from pypsrp.complex_objects import GenericComplexObject
from pypsrp.powershell import PowerShell, RunspacePool
from pypsrp.wsman import WSMan


def fetchDNS(network: Network) -> None:
    conf = utils.config()['plugins']['activedirectory']
    wsman = WSMan(
        server = conf['host'], 
        username = conf['username'], 
        password = conf['password'],
        ssl = False
    )
    with wsman, RunspacePool(wsman) as pool:
        zones = fetchZones(pool)
        records = fetchRecords(pool, zones.values())

        for record in records:
            details = record.adapted_properties
            fqdn, zoneName = parseDN(details['DistinguishedName'])
            if fqdn is not None and fqdn not in network.domains.exclusions:
                if fqdn.endswith('.in-addr.arpa'):
                    ip = '.'.join(fqdn.replace('.in-addr.arpa','').split('.')[::-1])
                    if ip not in network.ips:
                        network.add(IPv4Address(ip))
                    dnsobj = network.ips[ip]
                else:
                    if fqdn not in network.domains:
                        network.add(Domain(fqdn, zone = zoneName))
                    dnsobj = network.domains[fqdn]

                if details['RecordType'] == 'A':
                    dnsobj.link(details['RecordData'].adapted_properties['IPv4Address'], 'ActiveDirectory')

                elif details['RecordType'] == 'PTR':
                    dnsobj.link(details['RecordData'].adapted_properties['PtrDomainName'].strip('.'), 'ActiveDirectory')
                
                elif details['RecordType'] == 'CNAME':
                    value = details['RecordData'].adapted_properties['HostNameAlias']
                    if value.endswith('.'):
                        value = value.strip('.')
                    else:
                        value = value +'.'+ zoneName

                    if zones[zoneName].adapted_properties['IsReverseLookupZone']:
                        print('[DEBUG][activedirectory] Ignoring CNAME in reverse lookup zone')
                    else:
                        dnsobj.link(value, 'ActiveDirectory')


def fetchZones(pool: RunspacePool) -> dict[str, GenericComplexObject]:
    """
    Creates a new PowerShell in the pool and returns a dictionary of DNS zones.

    :param pool: The pool to start the new shell in.
    :type pool: RunspacePool
    :return: A dictionary mapping zone names to their objects.
    :rtype: dict[str, GenericComplexObject]
    """
    ps = PowerShell(pool)
    ps.add_cmdlet('Get-DnsServerZone')
    return {
        zone.adapted_properties['ZoneName']: zone
        for zone in ps.invoke()
    }


def fetchRecords(pool: RunspacePool, zones: Iterable[GenericComplexObject]) -> list[GenericComplexObject]:
    ps = PowerShell(pool)
    for zone in zones:
        zoneName = zone.adapted_properties['ZoneName']
        if not zoneName.startswith('_msdcs'):

            if zone.adapted_properties['IsReverseLookupZone']:
                ps.add_cmdlet('Get-DnsServerResourceRecord')\
                    .add_parameter('ZoneName', zoneName)\
                    .add_parameter('RRType', 'PTR')
                ps.add_statement()

            else:
                ps.add_cmdlet('Get-DnsServerResourceRecord')\
                    .add_parameter('ZoneName', zoneName)\
                    .add_parameter('RRType', 'A')
                ps.add_statement()
                    
                ps.add_cmdlet('Get-DnsServerResourceRecord')\
                    .add_parameter('ZoneName', zoneName)\
                    .add_parameter('RRType', 'CNAME')
                ps.add_statement()
    return ps.invoke()
    

dc_pattern = re.compile(r'DC\s*=\s*(?P<dc>.*)$', re.IGNORECASE)

def parseDN(distinguished_name: str) -> tuple[str, str]:
    """
    Parses a DistinguishedName as they appear in ActiveDirectory.

    :param distinguished_name: The DN of a DNS record
    :type distinguished_name: str
    :return: The FQDN and its parent DNS zone.
    :rtype: tuple[str, str]
    """
    name = []
    for statement in distinguished_name.split(','):
        match = re.match(dc_pattern, statement)
        if match:
            if match['dc'] == '*':
                name.append('_wildcard_')
            else:
                name.append(match['dc'])
        else:
            if name:
                if name[0] == '@':
                    fqdn = '.'.join(name[1:]).lower()
                    return fqdn, fqdn
                else:
                    return '.'.join(name).lower(), '.'.join(name[1:]).lower()
            else:
                return None, None


if __name__ == '__main__':
    n = Network()
    fetchDNS(n)
    n.dumpNetwork()

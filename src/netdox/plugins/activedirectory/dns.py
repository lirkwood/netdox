import logging
import re
from typing import Iterable, Optional

from pypsrp.complex_objects import GenericComplexObject
from pypsrp.powershell import PowerShell, RunspacePool
from pypsrp.wsman import WSMan

from netdox import utils
from netdox.iptools import ip_from_rdns_name
from netdox.containers import Network

logger = logging.getLogger(__name__)

def fetchDNS(network: Network) -> None:
    wsman = WSMan(**utils.config('activedirectory'), ssl = False)
    with wsman, RunspacePool(wsman) as pool:
        zones = fetchZones(pool)
        records = fetchRecords(pool, zones.values())

        for record in records:
            processRecord(network, record)


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

def parseDN(distinguished_name: str) -> tuple[Optional[str], Optional[str]]:
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
            name.append('_wildcard_' if match['dc'] == '*' else match['dc'])
        else:
            if name:
                if name[0] == '@':
                    fqdn = '.'.join(name[1:]).lower()
                    return fqdn, fqdn
                return '.'.join(name).lower(), '.'.join(name[1:]).lower()
            else:
                logger.debug('No hostname parsed from ' + distinguished_name)
                return None, None
    return None, None

def processRecord(network: Network, record: GenericComplexObject) -> None:
    """
    Creates a link in *network* that represents the DNS record *record*.

    :param network: The network to add the link to.
    :type network: Network
    :param record: The object that describes the DNS record.
    :type record: GenericComplexObject
    """
    details = record.adapted_properties
    fqdn, zoneName = parseDN(record.adapted_properties['DistinguishedName'])
    if fqdn is not None and fqdn not in network.config.exclusions:
        if fqdn.endswith('.in-addr.arpa'):
            fqdn = ip_from_rdns_name(fqdn)
        dnsobj = network.find_dns(fqdn)

        dest = ''
        record_data = details['RecordData'].adapted_properties
        if details['RecordType'] == 'A':
            dest = record_data['IPv4Address']
        elif details['RecordType'] == 'PTR':
            dest = record_data['PtrDomainName'].strip('.')
        elif details['RecordType'] == 'CNAME':
            dest = record_data['HostNameAlias']
            if dest.endswith('.in-addr.arpa'):
                dest = ip_from_rdns_name(dest)
            elif dest.endswith('.'):
                dest = dest.strip('.')
            elif zoneName:
                dest = dest +'.'+ zoneName
        
        if dest:
            dnsobj.link(dest, 'ActiveDirectory')
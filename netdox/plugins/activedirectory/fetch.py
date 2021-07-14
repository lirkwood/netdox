"""
Fetching data
*************

Used to read DNS records from ActiveDirectory.

Reads directory of JSON files, each corresponding to a DNS zone, and generates DNSRecords from them.
"""

import json

import iptools
import utils
from networkobjs import Domain, IPv4Address, Network


def fetchDNS(network: Network) -> None:
    """
    Iterates over each source JSON file and adds any DNSRecords found to the forward/reverse sets.

    :param network: The network
    :type network: Network
    """
    for file in utils.fileFetchRecursive('plugins/activedirectory/records', extension = '.json'):
        with open(file, 'r') as stream:
            try:
                jsondata = json.load(stream)
            except json.decoder.JSONDecodeError:
                print(f'[ERROR][ad_domains.py] Failed to parse file as json: {file.split("/")[-1]}')
            else:
                for record in jsondata:
                    if record['RecordType'] == 'A':
                        add_A(network, record)

                    elif record['RecordType'] == 'CNAME':
                        add_CNAME(network, record)
                    
                    elif record['RecordType'] == 'PTR':
                        add_PTR(network, record)


@utils.handle
def add_A(network: Network, record: dict):
    """
    Adds one A record to a Network from JSON returned by ActiveDirectory.

    :param network: The network.
    :type network: Network
    :param record: A dictionary containing some information about an A record.
    :type record: dict
    """
    # Get name
    distinguished_name = record['DistinguishedName'].split(',')    #get hostname
    subdomain = distinguished_name[0].replace('DC=', '') #extract subdomain
    root = distinguished_name[1].replace('DC=', '')    #extract root domain
    fqdn = assemble_fqdn(subdomain, root)

    if fqdn not in network.domains.exclusions:
        # Get value
        for item in record['RecordData']['CimInstanceProperties']:
            if item['Name'] == "IPv4Address":
                dest = item['Value'].strip('.')

        # Integrate
        if fqdn not in network.domains:
            network.add(Domain(fqdn, root))
        network.domains[fqdn].link(dest, 'ActiveDirectory')


@utils.handle
def add_CNAME(network: Network, record: dict):
    """
    Adds one CNAME record to a Network from JSON returned by ActiveDirectory.

    :param network: The network.
    :type network: Network
    :param record: A dictionary containing some information about a CNAME record.
    :type record: dict
    """
    distinguished_name = record['DistinguishedName'].split(',')
    subdomain = distinguished_name[0].strip('DC=')
    root = distinguished_name[1].strip('DC=')
    fqdn = assemble_fqdn(subdomain, root)
    
    if fqdn not in network.domains.exclusions:
        for item in record['RecordData']['CimInstanceProperties']:
            if item['Name'] == "HostNameAlias":
                dest = item['Value']
                if not dest.endswith('.'):
                    dest += '.'+ root
                else:
                    dest = dest.strip('.')

        if fqdn not in network.domains:
            network.add(Domain(fqdn, root))
        network.domains[fqdn].link(dest, 'ActiveDirectory')


@utils.handle
def add_PTR(network: Network, record: dict):
    """
    Adds one PTR record to a Network from JSON returned by ActiveDirectory.

    :param network: The network.
    :type network: Network
    :param record: A dictionary containing some information about a PTR record.
    :type record: dict
    """
    zone = record['DistinguishedName'].split(',')[1].strip('DC=')
    subnet = '.'.join(zone.replace('.in-addr.arpa','').split('.')[::-1])    #strip '.in-addr.arpa' and reverse octet order
    address = record['DistinguishedName'].split(',')[0].strip('DC=')        #... backwards subnet.
    ip = subnet +'.'+ address

    for item in record['RecordData']['CimInstanceProperties']:
        if item['Name'] == 'PtrDomainName':
            dest = item['Value'].strip('.')
    if iptools.valid_ip(ip):
        if ip not in network.ips:
            network.add(IPv4Address(ip))
        network.ips[ip].link(dest, 'ActiveDirectory')


def assemble_fqdn(subdomain: str, root: str) -> str:
    """
    Combines the subdomain and root as they are found in the AD JSON, to give a FQDN.

    :param subdomain: The subdomain of the FQDN.
    :type subdomain: str
    :param root: The root domain / DNS zone of the FQDN.
    :type root: str
    :return: A fully qualified domain name composed of the subdomain and root.
    :rtype: str
    """
    if subdomain == '@':
        fqdn = root
    elif subdomain == '*':
        fqdn = '_wildcard_.' + root
    elif root in subdomain:
        fqdn = subdomain
    else:
        fqdn = subdomain + '.' + root
    return fqdn.lower()
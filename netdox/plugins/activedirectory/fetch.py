"""
Fetching data
*************

Used to read DNS records from ActiveDirectory.

Reads directory of JSON files, each corresponding to a DNS zone, and generates DNSRecords from them.
"""

import os, json
import iptools, utils

def fetchDNS(forward: utils.DNSSet, reverse: utils.DNSSet):
    """
	Iterates over each source JSON file and adds any DNSRecords found to the forward/reverse sets.

    :Args:
        forward: DNSSet
            A forward DNSSet
        reverse: DNSSet
            A reverse DNSSet 
    """
    for file in fetchJson():
        with open(file, 'r') as stream:
            try:
                jsondata = json.load(stream)
            except json.decoder.JSONDecodeError:
                print(f'[ERROR][ad_domains.py] Failed to parse file as json: {file.name}')
            else:
                for record in jsondata:
                    if record['RecordType'] == 'A':
                        add_A(forward, record)

                    elif record['RecordType'] == 'CNAME':
                        add_CNAME(forward, record)
                    
                    elif record['RecordType'] == 'PTR':
                        add_PTR(reverse, record)


def fetchJson() -> os.DirEntry:
    """
    Generator which yields a json file containing some DNS records

    :Yields:
        A DirEntry pointing to a json file containing DNS records
    """
    for file in os.scandir("plugins/activedirectory/records/"):
        if file.name.endswith('.json'):
            yield file


@utils.handle
def add_A(dns_set: utils.DNSSet, record: dict):
    """
	Integrates one A record into a dns set from json given by ActiveDirectory

    :Args:
        dns_set: DNSSet
            A forward DNSSet to add a record to
        record: dict
            A JSON object describing a DNS A record
    """
    # Get name
    distinguished_name = record['DistinguishedName'].split(',')    #get hostname
    subdomain = distinguished_name[0].replace('DC=', '') #extract subdomain
    root = distinguished_name[1].replace('DC=', '')    #extract root domain
    fqdn = assemble_fqdn(subdomain, root)

    # Get value
    for item in record['RecordData']['CimInstanceProperties']:
        if item['Name'] == "IPv4Address":
            dest = item['Value'].strip('.')

    # Integrate
    if fqdn not in dns_set:
        dns_set.add(utils.DNSRecord(fqdn, root=root))
    dns_set[fqdn].link(dest, 'ipv4', 'ActiveDirectory')


@utils.handle
def add_CNAME(dns_set: utils.DNSSet, record: dict):
    """
	Integrates one CNAME record into a dns set from json given by ActiveDirectory

    :Args:
        dns_set: DNSSet
            A forward DNSSet to add a record to
        record: dict
            A JSON object describing a DNS CNAME record
    """
    distinguished_name = record['DistinguishedName'].split(',')
    subdomain = distinguished_name[0].strip('DC=')
    root = distinguished_name[1].strip('DC=')
    fqdn = assemble_fqdn(subdomain, root)
    
    for item in record['RecordData']['CimInstanceProperties']:
        if item['Name'] == "HostNameAlias":
            dest = item['Value']
            if not dest.endswith('.'):
                dest += '.'+ root
            else:
                dest = dest.strip('.')

    if fqdn not in dns_set:
        dns_set.add(utils.DNSRecord(fqdn, root=root))
    dns_set[fqdn].link(dest, 'domain', 'ActiveDirectory')


@utils.handle
def add_PTR(dns_set: utils.DNSSet, record: dict):
    """
	Integrates one PTR record into a dns set from json given by ActiveDirectory

    :Args:
        dns_set: DNSSet
            A reverse DNSSet to add a record to
        record: dict
            A JSON object describing a DNS PTR record
    """
    zone = record['DistinguishedName'].split(',')[1].strip('DC=')
    subnet = '.'.join(zone.replace('.in-addr.arpa','').split('.')[::-1])    #strip '.in-addr.arpa' and reverse octet order
    address = record['DistinguishedName'].split(',')[0].strip('DC=')        #... backwards subnet.
    ip = iptools.ipv4(subnet +'.'+ address)

    for item in record['RecordData']['CimInstanceProperties']:
        if item['Name'] == 'PtrDomainName':
            dest = item['Value'].strip('.')

    if ip.valid:
        if ip.ipv4 not in dns_set:
            dns_set.add(utils.PTRRecord(ip.ipv4, root=zone))
        dns_set[ip.ipv4].link(dest, 'ActiveDirectory')


def assemble_fqdn(subdomain: str, root: str) -> str:
    if subdomain == '@':
        fqdn = root
    elif subdomain == '*':
        fqdn = '_wildcard_.' + root
    elif root in subdomain:
        fqdn = subdomain
    else:
        fqdn = subdomain + '.' + root
    return fqdn.lower()
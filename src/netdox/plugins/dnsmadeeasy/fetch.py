"""
Fetching data
*************

Used to read DNS records from DNSMadeEasy.

Requests all managed domains and then all the records under each domain.
"""
import json
from typing import Generator, Tuple

import requests

from netdox import iptools, utils
from netdox.objs import Domain, IPv4Address, Network
from netdox.plugins.dnsmadeeasy import genheader


def fetchDomains() -> Generator[Tuple[str, str], None, None]:
    """
    Generator which returns a tuple containing one managed domain's ID and name.

    :yield: A 2-tuple containing the domain's ID and name as strings.
    :rtype: Generator[Tuple[str, str], None, None]
    """
    response = requests.get('https://api.dnsmadeeasy.com/V2.0/dns/managed/', headers=genheader()).text
    jsondata = json.loads(response)['data']
    if "error" in response:
        raise RuntimeError('DNSMadeEasy authentication failed.')
    else:
        for record in jsondata:
            yield (record['id'], record['name'])


def fetchDNS(network: Network):
    """
    Reads all DNS records from DNSMadeEasy and adds them to a Network object.

    :param network: The network.
    :type network: Network
    """
    for id, domain in fetchDomains():
        response = requests.get('https://api.dnsmadeeasy.com/V2.0/dns/managed/{0}/records'.format(id), headers=genheader()).text
        records = json.loads(response)['data']

        for record in records:
            if record['type'] == 'A':
                add_A(network, record, domain)
            
            elif record['type'] == 'CNAME':
                add_CNAME(network, record, domain)

            elif record['type'] == 'PTR':
                add_PTR(network, record, domain)


@utils.handle
def add_A(network: Network, record: dict, root: str):
    """
    Integrates one A record into a Network from a dictionary.

    :param network: The network.
    :type network: Network
    :param record: A dictionary containing some information about the record.
    :type record: dict
    :param root: The root domain this record belongs to.
    :type root: str
    """
    subdomain = record['name']
    ip = record['value']
    fqdn = assemble_fqdn(subdomain, root)

    if fqdn not in network.exclusions:
        network.domains[fqdn].link(ip, 'DNSMadeEasy')	

@utils.handle
def add_CNAME(network: Network, record: dict, root: str):
    """
    Integrates one CNAME record into a Network from a dictionary.

    :param network: The network.
    :type network: Network
    :param record: A dictionary containing some information about the record.
    :type record: dict
    :param root: The root domain this record belongs to.
    :type root: str
    """
    subdomain = record['name']
    value = record['value']
    fqdn = assemble_fqdn(subdomain, root)
    dest = assemble_fqdn(value, root)

    if fqdn not in network.exclusions:
        network.domains[fqdn].link(dest, 'DNSMadeEasy')

@utils.handle
def add_PTR(network: Network, record: dict, root: str):
    """
    Integrates one PTR record into a Network from a dictionary.

    :param network: The network.
    :type network: Network
    :param record: A dictionary containing some information about the record.
    :type record: dict
    :param root: The root domain this record belongs to.
    :type root: str
    """
    subnet = '.'.join(root.replace('.in-addr.arpa','').split('.')[::-1])
    addr = record['name']
    value = record['value']
    ip = subnet +'.'+ addr
    fqdn = assemble_fqdn(value, root)
    
    if iptools.valid_ip(ip):
        network.ips[ip].link(fqdn, 'DNSMadeEasy')


def assemble_fqdn(subdomain: str, root: str) -> str:
    """
    Combines the subdomain and root as they are found in the DNSME JSON, to give a FQDN.

    :param subdomain: The subdomain of the FQDN.
    :type subdomain: str
    :param root: The root domain / DNS zone of the FQDN.
    :type root: str
    :return: A fully qualified domain name composed of the subdomain and root.
    :rtype: str
    """
    if not subdomain:
        fqdn = root
    elif root in subdomain:
        fqdn = subdomain
    elif subdomain.endswith('.'):
        fqdn = subdomain
    elif subdomain == '*':
        fqdn = '_wildcard_.' + root
    else:
        fqdn = subdomain +'.'+ root
    return fqdn.strip('.').strip().lower()

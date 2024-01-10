"""
Fetching data
*************

Used to read DNS records from DNSMadeEasy.

Requests all managed domains and then all the records under each domain.
"""
import json
from typing import Generator, Tuple

import requests
from netdox import Network, utils
from datetime import datetime
import hmac
import hashlib

from netdox.dns import TXTRecord, CAARecord


def genheader() -> dict[str, str]:
	"""
	Generates authentication header for DNSME api

	:return: A dictionary of headers that can be passed to a requests request function.
	:rtype: dict[str, str]
	"""
	creds = utils.config('dnsmadeeasy')
	api = creds['api']
	secret = creds['secret']

	time = datetime.utcnow().strftime("%a, %d %b %Y %X GMT")
	hash_digest = hmac.new(
        key = bytes(secret, 'utf-8'), 
        msg = time.encode('utf-8'), 
        digestmod = hashlib.sha1
    ).hexdigest()
	
	header = {
	"x-dnsme-apiKey" : api,
	"x-dnsme-requestDate" : time,
	"x-dnsme-hmac" : hash_digest,
	"accept" : 'application/json'
	}
	
	return header


def fetch_domains() -> Generator[Tuple[str, str], None, None]:
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


def fetch_dns(network: Network):
    """
    Reads all DNS records from DNSMadeEasy and adds them to a Network object.

    :param network: The network.
    :type network: Network
    """
    for id, domain in fetch_domains():
        response = requests.get('https://api.dnsmadeeasy.com/V2.0/dns/managed/{0}/records'.format(id), headers=genheader()).text
        records = json.loads(response)['data']

        for record in records:
            if record['type'] == 'A':
                add_A(network, record, domain)
            
            elif record['type'] == 'CNAME':
                add_CNAME(network, record, domain)

            elif record['type'] == 'PTR':
                add_PTR(network, record, domain)

            elif record['type'] == 'TXT':
                add_TXT(network, record, domain)
            
            elif record['type'] == 'CAA':
                add_CAA(network, record, domain)

SOURCE = 'DNSMadeEasy'

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
    network.link(fqdn, ip, SOURCE)

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
    network.link(fqdn, dest, SOURCE)

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
    network.link(ip, fqdn, SOURCE)

@utils.handle
def add_TXT(network: Network, record: dict, root: str):
    """
    Integrates one TXT record into a Network from a dictionary.

    :param network: The network.
    :type network: Network
    :param record: A dictionary containing some information about the record.
    :type record: dict
    :param root: The root domain this record belongs to.
    :type root: str
    """
    subdomain = record['name']
    fqdn = assemble_fqdn(subdomain, root)
    network.domains[root].txt_records.add(
        TXTRecord(fqdn, record['value'], SOURCE))

@utils.handle
def add_CAA(network: Network, record: dict, root: str):
    """
    Integrates one CAA regord into a network from a dictionary.

    :param network: The network.
    :type network: Network
    :param record: A dictionary containing some information about the record.
    :type record: dict
    :param root: The root domain this record belongs to.
    :type root: str
    """
    subdomain = record['name']
    fqdn = assemble_fqdn(subdomain, root)
    network.domains[fqdn].caa_records.add(
        CAARecord(fqdn, record['value'], record['caaType'], SOURCE))


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

"""
Fetching data
*************

Used to read DNS records from DNSMadeEasy.

Requests all managed domains and then all the records under each domain.
"""
import json
from typing import Any, Generator, Tuple

import iptools
import requests
import utils
from networkobjs import Domain, IPv4Address, Network
from plugins.dnsmadeeasy import genheader


def fetchDomains() -> Generator[Tuple[str, str], Any, Any]:
	"""
	Generator which returns a tuple containing one managed domain's ID and name

	:Yields:
		Tuple[0]: str
			The ID of some managed domain
		Tuple[1]: str
			The name of the same domain
	"""
	response = requests.get('https://api.dnsmadeeasy.com/V2.0/dns/managed/', headers=genheader()).text
	jsondata = json.loads(response)['data']
	if "error" in response:
		print('[ERROR][dnsme_domains.py] DNSMadeEasy authentication failed.')
	else:
		for record in jsondata:
			yield (record['id'], record['name'])


def fetchDNS(network: Network):
	"""
	Reads all DNS records from DNSMadeEasy and adds them to a Network object

	:Args:
		network:
			A Network object
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
	Integrates one A record into a Network from json returned by DNSME api

	:Args:
		network:
			A Network object
		record: dict
			Some JSON describing a DNS record
		root: str
			The root domain the record comes from
	"""
	subdomain = record['name']
	ip = record['value']
	fqdn = assemble_fqdn(subdomain, root)

	if fqdn not in network.domains:
		network.add(Domain(fqdn, root))
	network.domains[fqdn].link(ip, 'DNSMadeEasy')	

@utils.handle
def add_CNAME(network: Network, record: dict, root: str):
	"""
	Integrates one CNAME record into a Network from json returned by DNSME api

	:Args:
		network:
			A Network object
		record: dict
			Some JSON describing a DNS record
		root: str
			The root domain the record comes from
	"""
	subdomain = record['name']
	value = record['value']
	fqdn = assemble_fqdn(subdomain, root)
	dest = assemble_fqdn(value, root)

	if fqdn not in network.domains:
		network.add(Domain(fqdn, root))
	network.domains[fqdn].link(dest, 'DNSMadeEasy')	

@utils.handle
def add_PTR(network: Network, record: dict, root: str):
	"""
	Integrates one PTR record into a Network from json returned by DNSME api

	:Args:
		network:
			A Network object
		record: dict
			Some JSON describing a DNS record
		root: str
			The root domain the record comes from
	"""
	subnet = '.'.join(root.replace('.in-addr.arpa','').split('.')[::-1])
	addr = record['name']
	value = record['value']
	ip = subnet +'.'+ addr
	fqdn = assemble_fqdn(value, root)
	
	if iptools.valid_ip(ip):
		if ip not in network.ips:
			network.add(IPv4Address(ip))
		network.ips[ip].link(fqdn, 'DNSMadeEasy')


def assemble_fqdn(subdomain: str, root: str) -> str:
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

"""
Fetching data
*************

Used to read DNS records from DNSMadeEasy.

Requests all managed domains and then all the records under each domain.
"""
from plugins.dnsmadeeasy import genheader
from typing import Any, Generator, Tuple
import json, requests
import iptools, utils



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


def fetchDNS(forward: utils.DNSSet, reverse: utils.DNSSet):
	"""
	Reads all DNS records from DNSMadeEasy and adds them to forward/reverse

	:Args:
		forward: DNSSet
			A forward DNS set
		reverse: DNSSet
			A reverse DNS set
	"""

	for id, domain in fetchDomains():
		response = requests.get('https://api.dnsmadeeasy.com/V2.0/dns/managed/{0}/records'.format(id), headers=genheader()).text
		records = json.loads(response)['data']

		for record in records:
			if record['type'] == 'A':
				add_A(forward, record, domain)
			
			elif record['type'] == 'CNAME':
				add_CNAME(forward, record, domain)

			elif record['type'] == 'PTR':
				add_PTR(reverse, record, domain)


@utils.handle
def add_A(dns_set: utils.DNSSet, record: dict, root: str):
	"""
	Integrates one A record into a dns set from json returned by DNSME api

	:Args:
		dns_set: DNSSet
			A forward DNS set
		record: dict
			Some JSON describing a DNS record
		root: str
			The root domain the record comes from
	"""
	subdomain = record['name']
	ip = record['value']
	fqdn = assemble_fqdn(subdomain, root)

	if fqdn not in dns_set:
		dns_set.add(utils.DNSRecord(fqdn, root=root))
	dns_set[fqdn].link(ip, 'ipv4', 'DNSMadeEasy')

@utils.handle
def add_CNAME(dns_set: utils.DNSSet, record: dict, root: str):
	"""
	Integrates one CNAME record into a dns set from json returned by DNSME api

	:Args:
		dns_set: DNSSet
			A forward DNS set
		record: dict
			Some JSON describing a DNS record
		root: str
			The root domain the record comes from
	"""
	subdomain = record['name']
	value = record['value']
	fqdn = assemble_fqdn(subdomain, root)
	dest = assemble_fqdn(value, root)

	if fqdn not in dns_set:
		dns_set.add(utils.DNSRecord(fqdn, root=root))
	dns_set[fqdn].link(dest, 'domain', 'DNSMadeEasy')	

@utils.handle
def add_PTR(dns_set: utils.DNSSet, record: dict, root: str):
	"""
	Integrates one PTR record into a dns set from json returned by DNSME api

	:Args:
		dns_set: DNSSet
			A reverse DNS set
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
		if ip not in dns_set:
			dns_set.add(utils.PTRRecord(ip, source='DNSMadeEasy', root=root))
		dns_set[ip].link(fqdn, 'DNSMadeEasy')


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
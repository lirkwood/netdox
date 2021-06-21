from plugins.dnsmadeeasy import genheader
from typing import Any, Generator, Tuple
import json, requests
import iptools, utils



def fetchDomains() -> Generator[Tuple[str, str], Any, Any]:
	"""
	Generator which returns a tuple containing one managed domain's ID and name
	"""
	response = requests.get('https://api.dnsmadeeasy.com/V2.0/dns/managed/', headers=genheader()).text
	jsondata = json.loads(response)['data']
	if "error" in response:
		print('[ERROR][dnsme_domains.py] DNSMadeEasy authentication failed.')
	else:
		for record in jsondata:
			yield (record['id'], record['name'])


def fetchDNS(forward: dict[str, utils.DNSRecord], reverse: dict[str, utils.DNSRecord]):
	"""
	Returns tuple containing forward and reverse DNS records from DNSMadeEasy
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
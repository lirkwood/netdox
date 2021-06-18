from datetime import datetime
import re, hmac, json, hashlib, requests
from typing import Any, Generator, Tuple
import iptools, utils


def genheader() -> dict[str, str]:
	"""
	Generates authentication header for DNSME api
	"""
	creds = utils.auth()['plugins']['dnsmadeeasy']
	api = creds['api']
	secret = creds['secret']

	time = datetime.utcnow().strftime("%a, %d %b %Y %X GMT")
	hash = hmac.new(bytes(secret, 'utf-8'), msg=time.encode('utf-8'), digestmod=hashlib.sha1).hexdigest()
	
	header = {
	"x-dnsme-apiKey" : api,
	"x-dnsme-requestDate" : time,
	"x-dnsme-hmac" : hash,
	"accept" : 'application/json'
	}
	
	return header


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


@utils.handle
def create_A(name: str, ip: str, zone: str):
	"""
	Creates an A record in DNSMadeEasy
	"""
	if re.fullmatch(utils.dns_name_pattern, name) and iptools.valid_ip(ip):
		with open('src/forward.json') as stream:
			dns = utils.DNSSet.from_json(stream.read())
		if (ip, 'DNSMadeEasy') in dns[name]._ips:
			return None

		with open('plugin/dnsmadeeasy/src/zones.json', 'r') as zonestream:
			zones = json.load(zonestream)
			if zone in zones:
				endpoint = f'https://api.dnsmadeeasy.com/V2.0/dns/managed/{zones[zone]}/records/'
				data = {
					"name": name,
					"type": "A",
					"value": ip,
					"gtdLocation": "DEFAULT",
					"ttl": 1800
				}
				# r = requests.post(endpoint, headers=genheader(), data=data)
				# return r.text
				print(endpoint)
				return None
			else:
				raise ValueError(f'[ERROR][dnsme_api.py] Unknown zone for DNSMadeEasy: {zone}')
	else:
		raise ValueError(f'[ERROR][dnsme_api.py] Invalid hostname ({name}) or IPv4 ({ip})')

@utils.handle
def create_CNAME(name: str, value: str, zone: str):
	"""
	Creates a CNAME record in DNSMadeEasy
	"""
	if re.fullmatch(utils.dns_name_pattern, name) and re.fullmatch(utils.dns_name_pattern, value):
		with open('src/forward.json') as stream:
			dns = utils.DNSSet.from_json(stream.read())
		if (value, 'DNSMadeEasy') in dns[name]._cnames:
			return None

		with open('src/zones.json', 'r') as stream:
			zones = json.load(stream)
			if zone in zones:
				endpoint = f'https://api.dnsmadeeasy.com/V2.0/dns/managed/{zones[zone]}/records/'
				data = {
					"name": name,
					"type": "CNAME",
					"value": value,
					"gtdLocation": "DEFAULT",
					"ttl": 1800
				}
				# r = requests.post(endpoint, headers=genheader(), data=data)
				# return r.text
				print(endpoint)
				return None

			else:
				raise ValueError(f'[ERROR][dnsme_api.py] Unknown zone for DNSMadeEasy: {zone}')
	else:
		raise ValueError(f'[ERROR][dnsme_api.py] Invalid hostname ({name}) or ({value})')

@utils.handle
def create_PTR(ip: str, value: str):
	"""
	Creates a PTR record in DNSMadeEasy
	"""
	if iptools.valid_ip(ip) and re.fullmatch(utils.dns_name_pattern, value):
		with open('src/ips.json', 'r') as dnsstream:
			dns = json.load(dnsstream)
			if [value, 'DNSMadeEasy'] in dns[ip]['_ptr']:
				return None

		addr = ip.split('.')[-1]
		zone = f'{".".join(ip.split(".")[-2::-1])}.in-addr.arpa'
		with open('src/zones.json', 'r') as stream:
			zones = json.load(stream)
			if zone in zones:
				endpoint = f'https://api.dnsmadeeasy.com/V2.0/dns/managed/{zones[zone]}/records/'
				data = {
					"name": addr,
					"type": "PTR",
					"value": value,
					"gtdLocation": "DEFAULT",
					"ttl": 3600
				}
				# r = requests.post(endpoint, headers=genheader(), data=data)
				# return r.text
				print(endpoint)
				return None

			else:
				raise ValueError(f'[ERROR][dnsme_api.py] Unknown zone for DNSMadeEasy: {zone}')
	else:
		raise ValueError(f'[ERROR][dnsme_api.py] Invalid IPv4 ({ip}) or hostname ({value})')
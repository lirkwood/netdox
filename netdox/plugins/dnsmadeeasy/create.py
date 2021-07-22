"""
Creating Records
****************

Provides some functions for creating DNS records in DNSMadeEasy
"""
import networkobjs
import utils, iptools
import re, json

@utils.handle
def create_A(name: str, ip: str, zone: str) -> None:
	"""
	Creates an A record in DNSMadeEasy

	:param name: The name for the record.
	:type name: str
	:param ip: The ip for the record.
	:type ip: str
	:param zone: The DNS zone to create the record in.
	:type zone: str
	:raises ValueError: If the DNS zone is not one of the configured values
	:raises ValueError: If *name* is not a valid FQDN or *ip* is not a valid IPv4 address.
	"""
	if re.fullmatch(utils.dns_name_pattern, name) and iptools.valid_ip(ip):
			
		domains = networkobjs.DomainSet.from_json('src/domains.json')
		if (ip, 'DNSMadeEasy') in domains[name]._ips:
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
				raise ValueError(f'[ERROR][dnsmadeeasy] Unknown zone for DNSMadeEasy: {zone}')
	else:
		raise ValueError(f'[ERROR][dnsmadeeasy] Invalid hostname ({name}) or IPv4 ({ip})')

@utils.handle
def create_CNAME(name: str, value: str, zone: str) -> None:
	"""
	Creates an CNAME record in DNSMadeEasy

	:param name: The name for the record.
	:type name: str
	:param value: The value for the record.
	:type value: str
	:param zone: The DNS zone to create the record in.
	:type zone: str
	:raises ValueError: If the DNS zone is not one of the configured values
	:raises ValueError: If *name* or *value* is not a valid FQDN
	"""
	if re.fullmatch(utils.dns_name_pattern, name) and re.fullmatch(utils.dns_name_pattern, value):

		domains = networkobjs.DomainSet.from_json('src/domains.json')
		if (value, 'DNSMadeEasy') in domains[name]._cnames:
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
				raise ValueError(f'[ERROR][dnsmadeeasy] Unknown zone for DNSMadeEasy: {zone}')
	else:
		raise ValueError(f'[ERROR][dnsmadeeasy] Invalid hostname ({name}) or ({value})')

@utils.handle
def create_PTR(ip: str, value: str) -> None:
	"""
	Creates an PTR record in DNSMadeEasy.

	:param ip: The ip to use for the name of the record.
	:type ip: str
	:param value: The value for the recod.
	:type value: str
	:raises ValueError: If the DNS zone is not one of the configured values
	:raises ValueError: If *ip* is not a valid IPv4 address or *value* is not a valid FQDN.
	"""
	if iptools.valid_ip(ip) and re.fullmatch(utils.dns_name_pattern, value):

		ips = networkobjs.IPv4AddressSet.from_json('src/ips.json')
		if (value, 'DNSMadeEasy') in ips[ip]._ptr:
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
				raise ValueError(f'[ERROR][dnsmadeeasy] Unknown zone for DNSMadeEasy: {zone}')
	else:
		raise ValueError(f'[ERROR][dnsmadeeasy] Invalid IPv4 ({ip}) or hostname ({value})')
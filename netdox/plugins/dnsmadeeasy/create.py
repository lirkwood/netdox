import utils, iptools
import re, json

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
		with open('src/reverse.json', 'r') as dnsstream:
			dns = utils.DNSSet(dnsstream.read())
			if (value, 'DNSMadeEasy') in dns[ip]._ptr:
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
from datetime import datetime
import re, hmac, json, hashlib, requests
import iptools, utils


def genheader():
	"""
	Generates authentication header for DNSME api
	"""
	with open('src/authentication.json','r') as stream:
		creds = json.load(stream)['dnsmadeeasy']
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


def fetchDomains():
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


@utils.critical
def fetchDNS():
	"""
	Returns tuple containing forward and reverse DNS records from DNSMadeEasy
	"""
	forward = {}
	reverse = {}

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

	return (forward, reverse)


@utils.handle
def add_A(dns_set, record, root):
	"""
	Integrates one A record into a dns set from json returned by DNSME api
	"""
	subdomain = record['name']
	ip = record['value']
	fqdn = assemble_fqdn(subdomain, root)

	if fqdn not in dns_set:
		dns_set[fqdn] = utils.dns(fqdn, source='DNSMadeEasy', root=root)
	dns_set[fqdn].link(ip, 'ipv4')

@utils.handle
def add_CNAME(dns_set, record, root):
	"""
	Integrates one CNAME record into a dns set from json returned by DNSME api
	"""
	subdomain = record['name']
	value = record['value']
	fqdn = assemble_fqdn(subdomain, root)
	dest = assemble_fqdn(value, root)

	if fqdn not in dns_set:
		dns_set[fqdn] = utils.dns(fqdn, source='DNSMadeEasy', root=root)
	dns_set[fqdn].link(dest, 'domain')	

@utils.handle
def add_PTR(dns_set, record, root):
	"""
	Integrates one PTR record into a dns set from json returned by DNSME api
	"""
	subnet = '.'.join(root.replace('.in-addr.arpa','').split('.')[::-1])
	addr = record['name']
	value = record['value']
	ip = addr +'.'+ subnet
	fqdn = assemble_fqdn(value, root)
	
	if iptools.valid_ip(ip):
		if ip not in dns_set:
			dns_set[ip] = utils.ptr(ip, source='DNSMadeEasy', root=root)
		dns_set[ip].link(fqdn)


def assemble_fqdn(subdomain, root):
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
	return fqdn.strip('.').strip()


@utils.handle
def create_A(name, zone, ip):
	if re.fullmatch(utils.dns_name_pattern, name) and iptools.valid_ip(ip):
		with open('src/zones.json', 'r') as stream:
			zones = json.load(stream)['dnsme']
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
def create_CNAME(name, zone, value):
	if re.fullmatch(utils.dns_name_pattern, name) and re.fullmatch(utils.dns_name_pattern, value):
		with open('src/zones.json', 'r') as stream:
			zones = json.load(stream)['dnsme']
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
def create_PTR(addr, zone, value):
	if int(addr) and re.fullmatch(utils.dns_name_pattern, value):
		with open('src/zones.json', 'r') as stream:
			zones = json.load(stream)['dnsme']
			if zone in zones:
				endpoint = f'https://api.dnsmadeeasy.com/V2.0/dns/managed/{zones[zone]}/records/'
				data = {
					"name": addr,
					"type": "CNAME",
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
		raise ValueError(f'[ERROR][dnsme_api.py] Invalid address ({addr}) or hostname ({value})')
from datetime import datetime
import hmac, json, hashlib, requests
import iptools, utils

##################################################################################
# requests all domains from dnsme, and then all of their associated dns records. #
##################################################################################

@utils.critical
def main():
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
				forward = add_A(record, domain, forward)
			
			elif record['type'] == 'CNAME':
				forward = add_CNAME(record, domain, forward)

			elif record['type'] == 'PTR':
				reverse = add_PTR(record, domain, reverse)

	return (forward, reverse)


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


def add_A(record, root, dns_set):
	"""
	Integrates one A record into a dns set from json returned by DNSME api
	"""
	subdomain = record['name']
	ip = record['value']
	fqdn = assemble_fqdn(subdomain, root)

	if fqdn not in dns_set:
		dns_set[fqdn] = utils.dns(fqdn, source='DNSMadeEasy', root=root)
	dns_set[fqdn].link(ip, 'ipv4')

	return dns_set


def add_CNAME(record, root, dns_set):
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

	return dns_set


def add_PTR(record, root, dns_set):
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
			dns_set[ip] = []
		dns_set[ip].append(fqdn)
	
	return dns_set


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
	return fqdn
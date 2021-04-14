from json.decoder import JSONDecodeError
from requests import get
import hmac, hashlib
import datetime
import iptools
import utils
import json
import os

##################################################################################
# requests all domains from dnsme, and then all of their associated dns records. #
##################################################################################

@utils.critical
def main():
	forward = {}
	reverse = {}

	for id, domain in fetchDomains():
		header = genheader()

		response = get('https://api.dnsmadeeasy.com/V2.0/dns/managed/{0}/records'.format(id), headers=header).text
		records = json.loads(response)['data']

		for record in records:
			if record['type'] == 'A':
				forward = add_A(record, domain, forward)
			
			elif record['type'] == 'CNAME':
				name = record['name'] +'.'+ domain
				value = record['value']
				name = name.replace('*.','_wildcard_.')

				if len(value) == 0:
					value = domain
				elif value.endswith('.'):
					value = value.strip('.')
				else:
					value += '.'+ domain
				if name not in forward:
					forward[name] = utils.dns(name, source='DNSMadeEasy', root=domain)
				forward[name].link(value, 'domain')

			elif record['type'] == 'PTR':
				subnet = '.'.join(domain.replace('.in-addr.arpa','').split('.')[::-1])
				ip = iptools.ipv4(subnet +'.'+ record['name'])
				value = record['value'].strip('.')
				
				if ip.valid:
					if ip.ipv4 not in reverse:
						reverse[ip.ipv4] = []
					reverse[ip.ipv4].append(value)

	return (forward, reverse)


def genheader():
	with open('src/authentication.json','r') as stream:
		creds = json.load(stream)['dnsmadeeasy']
		api = creds['api']
		secret = creds['secret']

		time = datetime.datetime.utcnow().strftime("%a, %d %b %Y %X GMT")
		hash = hmac.new(bytes(secret, 'utf-8'), msg=time.encode('utf-8'), digestmod=hashlib.sha1).hexdigest()
		
		header = {
		"x-dnsme-apiKey" : api,
		"x-dnsme-requestDate" : time,
		"x-dnsme-hmac" : hash,
		"accept" : 'application/json'
		}
		
		return header


def fetchDomains():
	response = get('https://api.dnsmadeeasy.com/V2.0/dns/managed/', headers=genheader()).text
	jsondata = json.loads(response)['data']
	if "error" in response:
		print('[ERROR][dnsme_domains.py] DNSMadeEasy authentication failed.')
	else:
		for record in jsondata:
			yield (record['id'], record['name'])


def add_A(record, root, dns_set):
	subdomain = record['name']
	ip = record['value']
	fqdn = assemble_fqdn(subdomain, root)

	if fqdn not in dns_set:
		dns_set[fqdn] = utils.dns(fqdn, source='DNSMadeEasy', root=root)
	dns_set[fqdn].link(ip, 'ipv4')

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

if __name__ == '__main__':
	main()

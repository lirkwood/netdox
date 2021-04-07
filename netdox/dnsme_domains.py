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

def main():
	master = {'forward': {}, 'reverse': {}}
	forward = master['forward']
	reverse = master['reverse']

	header = genheader()
	if not header:
		return master

	r = get('https://api.dnsmadeeasy.com/V2.0/dns/managed/', headers=header)
	response = json.loads(r.text)
	if "error" in response:
		print('[ERROR][dnsme_domains.py] DNSMadeEasy authentication failed.')
		return master
	domains = {}
	for record in response['data']:
		if record['id'] not in domains:
			domains[record['id']] = record['name']
	
	for id in domains:
		domain = domains[id]

		header = genheader()

		r = get('https://api.dnsmadeeasy.com/V2.0/dns/managed/{0}/records'.format(id), headers=header)
		records = json.loads(r.text)

		for record in records['data']:
			if record['type'] == 'A':
				name = record['name']

				if len(name) == 0:
					name = domain
				elif domain in name:
					pass
				elif not name.endswith('.'):
					name += '.'+ domain

				name = name.replace('*.','_wildcard_.')
				if name not in forward:
					forward[name] = utils.dns(name)
					forward[name].source = 'DNSMadeEasy'
				forward[name].destinations(record['value'], 'ipv4')
			
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
					forward[name] = utils.dns(name)
					forward[name].source = 'DNSMadeEasy'
				forward[name].destinations(record['value'], 'domain')

			elif record['type'] == 'PTR':
				subnet = '.'.join(domain.replace('.in-addr.arpa','').split('.')[::-1])
				ip = iptools.ipv4(subnet +'.'+ record['name'])
				value = record['value'].strip('.')
				
				if ip.valid:
					if ip.ipv4 not in reverse:
						reverse[ip.ipv4] = []
					reverse[ip.ipv4].append(value)

	return master


def genheader():
	try:
		with open('src/authentication.json','r') as stream:
			try:
				keys = json.load(stream)
				api = keys['dnsmadeeasy']['api']
				secret = keys['dnsmadeeasy']['secret']
			except JSONDecodeError:
				print('[ERROR][dnsme_domains.py] Incorrect formatting in src/authentication.json. Unable to read details.')
				return None
			except KeyError:
				print('[ERROR][dnsme_domains.py] Missing or corrupted authentication details')
				return None
			else:
				if api != '' and secret != '':
					time = datetime.datetime.utcnow().strftime("%a, %d %b %Y %X GMT")
					hash = hmac.new(bytes(secret, 'utf-8'), msg=time.encode('utf-8'), digestmod=hashlib.sha1).hexdigest()
					
					header = {	#populate header
					"x-dnsme-apiKey" : api,
					"x-dnsme-requestDate" : time,
					"x-dnsme-hmac" : hash,
					"accept" : 'application/json'
					}
					
					return header
				else:
					return None

	except FileNotFoundError:
		print('[ERROR][dnsme_domains.py] Missing or inaccessible src/authentication.json')
		return None


	#create hash using secret key as key (as a bytes literal), the time (encoded) in sha1 mode, output as hex

if __name__ == '__main__':
	main()

from getpass import getpass
from requests import get
import hmac, hashlib
import datetime
import iptools
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
		print('DNSMadeEasy authentication failed. Clearing bad authentication data...')
		os.remove('src/dnsme.txt')
		return main()
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
					forward[name] = {'dest': {'ips': [], 'domains': [], 'apps': []}, 'root': domain, 'source': 'DNSMadeEasy'}
				forward[name]['dest']['ips'].append(record['value'])
			
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
					forward[name] = {'dest': {'ips': [], 'domains': [], 'apps': []}, 'root': domain, 'source': 'DNSMadeEasy'}
				forward[name]['dest']['domains'].append(value)

			elif record['type'] == 'PTR':
				subnet = '.'.join(domain.replace('.in-addr.arpa','').split('.')[::-1])
				ip = iptools.parsed_ip(subnet +'.'+ record['name'])
				value = record['value'].strip('.')
				
				if ip.valid:
					if ip.ipv4 not in reverse:
						reverse[ip.ipv4] = []
					reverse[ip.ipv4].append(value)

	return master


def genheader():
	try:
		with open('src/dnsme.txt','r') as keys:
			api = keys.readline().strip()
			secret = keys.readline().strip()
			time = datetime.datetime.utcnow().strftime("%a, %d %b %Y %X GMT")
			hash = hmac.new(bytes(secret, 'utf-8'), msg=time.encode('utf-8'), digestmod=hashlib.sha1).hexdigest()
			
			header = {	#populate header
			"x-dnsme-apiKey" : api,
			"x-dnsme-requestDate" : time,
			"x-dnsme-hmac" : hash,
			"accept" : 'application/json'
			}
			
			return header
		#create hash using secret key as key (as a bytes literal), the time (encoded) in sha1 mode, output as hex
	except FileNotFoundError:
		return noauth()

def noauth():
	choice = input('***ALERT***\nNo DNSMadeEasy authentication details detected. Do you wish to enter them now? (y/n): ')
	if choice == 'y':
		with open('src/dnsme.txt','w') as keys:
			keys.write(getpass('Enter the DNSMadeEasy API key: '))
			keys.write('\n')
			keys.write(getpass('Enter the DNSMadeEasy secret key: '))
		return genheader()
	elif choice == 'n':
		print('Proceeding without DNSMadeEasy data...')
		return None
	else:
		print("Invalid input. Enter 'y' or 'n'.")
		return noauth()

if __name__ == '__main__':
	main()

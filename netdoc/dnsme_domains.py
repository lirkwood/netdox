from requests import get
import hmac, hashlib
import datetime
import json

##################################################################################
# requests all domains from dnsme, and then all of their associated dns records. #
##################################################################################

def main():
	master = {}

	header = genheader()
	r = get('https://api.dnsmadeeasy.com/V2.0/dns/managed/', headers=header)
	response = json.loads(r.text)
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
				if name not in master:
					master[name] = {'aliases': [], 'ips': [], 'root': domain, 'source': 'DNSMadeEasy'}
				master[name]['ips'].append(record['value'])

		for record in records['data']:
			if record['type'] == 'CNAME':
				name = record['name'] +'.'+ domain
				value = record['value']
				name = name.replace('*.','_wildcard_.')

				if len(value) == 0:
					value = domain
				elif value.endswith('.'):
					value = value.strip('.')
				else:
					value += '.'+ domain
				if value in master:
					master[value]['aliases'].append(name)
				else:
					# print('CNAME with no A record: '+ name)
					pass
				
	return master


def genheader():
	with open('Sources/dnsme.txt','r') as keys:
		api = keys.readline().split()[-1]
		secret = keys.readline().split()[-1]
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

if __name__ == '__main__':
	main()

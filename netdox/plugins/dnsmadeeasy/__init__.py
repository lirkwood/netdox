"""
Used to read and modify DNS records stored in DNSMadeEasy.
"""
import hashlib
import hmac
import json
import os
from datetime import datetime

import utils
from networkobjs import Network
from plugins import Plugin as BasePlugin


def genheader() -> dict[str, str]:
	"""
	Generates authentication header for DNSME api

	:return: A dictionary of headers that can be passed to a requests request function.
	:rtype: dict[str, str]
	"""
	creds = utils.config()['plugins']['dnsmadeeasy']
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


from plugins.dnsmadeeasy.create import create_A, create_CNAME, create_PTR
from plugins.dnsmadeeasy.fetch import fetchDNS, fetchDomains


class Plugin(BasePlugin):
	name = 'dnsmadeeasy'
	stages = ['dns']

	def init(self) -> None:
		zones = {}
		for id, domain in fetchDomains():
			zones[domain] = id

		if not os.path.exists('plugins/dnsmadeeasy/src'):
			os.mkdir('plugins/dnsmadeeasy/src')
		with open('plugins/dnsmadeeasy/src/zones.json', 'w') as stream:
			stream.write(json.dumps(zones, indent=2))

	def runner(self, network: Network, *_) -> None:
		fetchDNS(network)

	def create_A(self, name:str, ip: str, zone: str) -> None:
		create_A(name, ip, zone)

	def create_CNAME(self, name: str, value: str, zone: str) -> None:
		create_CNAME(name, value, zone)

	def create_PTR(self, ip: str, value: str) -> None:
		create_PTR(ip, value)


## Imports

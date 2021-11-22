"""
Used to read and modify DNS records stored in DNSMadeEasy.
"""
import hashlib
import hmac
import json
import os
from datetime import datetime

from netdox import utils


def genheader() -> dict[str, str]:
	"""
	Generates authentication header for DNSME api

	:return: A dictionary of headers that can be passed to a requests request function.
	:rtype: dict[str, str]
	"""
	creds = utils.config('dnsmadeeasy')
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


from netdox.plugins.dnsmadeeasy.create import (create_A, create_CNAME,
                                               create_PTR)
from netdox.plugins.dnsmadeeasy.fetch import fetchDNS, fetchDomains


__stages__ = {'dns': fetchDNS}
__config__ = {'api': str, 'secret': str}


def init() -> None:
	zones = {}
	for id, domain in fetchDomains():
		zones[domain] = id

	if not os.path.exists(utils.APPDIR+ 'plugins/dnsmadeeasy/src'):
		os.mkdir(utils.APPDIR+ 'plugins/dnsmadeeasy/src')
	with open(utils.APPDIR+ 'plugins/dnsmadeeasy/src/zones.json', 'w') as stream:
		stream.write(json.dumps(zones, indent=2))

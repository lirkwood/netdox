import utils, json, os
import hashlib, hmac
from datetime import datetime
stage = 'dns'

def genheader() -> dict[str, str]:
	"""
	Generates authentication header for DNSME api
	"""
	creds = utils.auth()['plugins']['dnsmadeeasy']
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

def init():
    zones = {}
    for id, domain in fetchDomains():
        zones[domain] = id

    if not os.path.exists('plugins/dnsmadeeasy/src'):
        os.mkdir('plugins/dnsmadeeasy/src')
    with open('plugins/dnsmadeeasy/src/zones.json', 'w') as stream:
        stream.write(json.dumps(zones, indent=2))


## Imports
from plugins.dnsmadeeasy.fetch import fetchDNS as runner
from plugins.dnsmadeeasy.fetch import fetchDomains
from plugins.dnsmadeeasy.create import create_A, create_CNAME, create_PTR
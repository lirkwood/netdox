from plugins.dnsmadeeasy.dnsme_api import fetchDNS as runner
from plugins.dnsmadeeasy.dnsme_api import fetchDomains
import json, os
stage = 'dns'

zones = {}
for id, domain in fetchDomains():
    zones[domain] = id

if not os.path.exists('plugins/dnsmadeeasy/src'):
    os.mkdir('plugins/dnsmadeeasy/src')
with open('plugins/dnsmadeeasy/src/zones.json', 'w') as stream:
    stream.write(json.dumps(zones, indent=2))


## DNS Actions
from plugins.dnsmadeeasy.dnsme_api import create_A, create_CNAME, create_PTR
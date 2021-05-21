from plugins.dnsmadeeasy.dnsme_api import fetchDNS as runner
from plugins.dnsmadeeasy.dnsme_api import fetchDomains
import json, os
stage = 'dns'


zones = {
    "dnsme": {},
    "ad": {},
    "k8s": {},
    "cf": {}
}    

for id, domain in fetchDomains():
    zones['dnsme'][domain] = id

if not os.path.exists('plugins/dnsmadeeasy/src'):
    os.mkdir('plugins/dnsmadeeasy/src')
with open('plugins/dnsmadeeasy/src/zones.json', 'w') as stream:
    stream.write(json.dumps(zones, indent=2))
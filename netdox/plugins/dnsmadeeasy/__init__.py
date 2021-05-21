from plugins.dnsmadeeasy.dnsme_api import fetchDNS as runner
from plugins.dnsmadeeasy.dnsme_api import fetchDomains
import json
stage = 'dns'


zones = {
    "dnsme": {},
    "ad": {},
    "k8s": {},
    "cf": {}
}    

for id, domain in fetchDomains():
    zones['dnsme'][domain] = id

with open('plugins/dnsmadeeasy/src/zones.json', 'w') as stream:
    stream.write(json.dumps(zones, indent=2))
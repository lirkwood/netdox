import ad_domains
import dnsme_domains
import binary
import test

import json
import os
    
print('Removing old documents...')
if not os.path.exists('../outgoing/DNS'):
    os.mkdir('../outgoing/DNS')
else: 
    for f in os.scandir('../outgoing/DNS'):
        os.remove(f)
        
if not os.path.exists('../outgoing/IPs'):
    os.mkdir('../outgoing/IPs')
else:
    for f in os.scandir('../outgoing/IPs'):
        os.remove(f)
os.remove('../Sources/domains.json')
print('Done.')

ad = ad_domains.main()
print('Active Directory domains processed')
dnsme = dnsme_domains.main()
print('DNSMadeEasy domains processed')

master = dict(ad)
for domain in dnsme:
    if domain in master:
        for ip in dnsme[domain]['ips']:
            master[domain]['ips'].append(ip)
        for alias in dnsme[domain]['aliases']:
            master[domain]['aliases'].append(alias)
    else:
        master[domain] = dnsme[domain]


for domain in master:   #adding subnets
    master[domain]['ips'] = list(dict.fromkeys(master[domain]['ips']))
    master[domain]['aliases'] = list(dict.fromkeys(master[domain]['aliases']))
    master[domain]['subnet'] = []
    for i in range(len(master[domain]['ips'])):
        ip = master[domain]['ips'][i]
        if test.valid_ip(ip):
            master[domain]['subnet'].append(binary.netbox_sort(ip))
        else:
            master[domain]['ips'].pop(i)
            print('Removed invalid ip: '+ ip)
    
with open('../Sources/domains.json','w') as stream:
    stream.write(json.dumps(master, indent=2))


print('DNS documents done')

import ipdocs
ipdocs.main()

print('IP documents done')
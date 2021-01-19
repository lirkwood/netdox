import ad_domains
import dnsme_domains
import binary
import test

import subprocess
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
print('Done.')

ad = ad_domains.main()
print('Active Directory domains processed.')
dnsme = dnsme_domains.main()
print('DNSMadeEasy domains processed.')

master = {}
for domain in ad:
    master[domain.lower()] = ad[domain]
for domain in dnsme:
    if domain in master:
        for ip in dnsme[domain]['ips']:
            master[domain]['ips'].append(ip)
        for alias in dnsme[domain]['aliases']:
            master[domain]['aliases'].append(alias)
    else:
        master[domain] = dnsme[domain]

iplist = {}
for domain in master:   #adding subnets
    master[domain]['ips'] = list(dict.fromkeys(master[domain]['ips']))
    master[domain]['aliases'] = list(dict.fromkeys(master[domain]['aliases']))
    master[domain]['subnets'] = []
    for i in range(len(master[domain]['ips'])):
        ip = master[domain]['ips'][i]
        if test.valid_ip(ip):
            master[domain]['subnets'].append(binary.netbox_sort(ip))
            iplist[ip] = master[domain]['source']
        else:
            master[domain]['ips'].pop(i)
            print('Removed invalid ip: '+ ip)
    for i in range(len(master[domain]['aliases'])):
        alias = master[domain]['aliases'][i]
        if '_wildcard_' in alias:
            alias = alias.replace('_wildcard_','*')
    
with open('../Sources/domains.json','w') as stream:
    stream.write(json.dumps(master, indent=2))

subprocess.run('java -jar c:/saxon/saxon-he-10.3.jar -xsl:dns.xsl -s:../Sources/domains.xml')

print('DNS documents done')

import ipdocs
ipdocs.main(iplist)

print('IP documents done')
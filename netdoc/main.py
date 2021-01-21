import ad_domains
import dnsme_domains
import iptools

import subprocess
import json
import os
    
print('Removing old documents...')
if not os.path.exists('outgoing'):
    os.mkdir('outgoing')
if not os.path.exists('outgoing/DNS'):
    os.mkdir('outgoing/DNS')
else: 
    for f in os.scandir('outgoing/DNS'):
        os.remove(f)
        
if not os.path.exists('outgoing/IPs'):
    os.mkdir('outgoing/IPs')
else:
    for f in os.scandir('outgoing/IPs'):
        os.remove(f)
print('Done.')

subprocess.run('pwsh.exe ./get-ad.ps1')
ad = ad_domains.main()
print('Active Directory domains processed.')
dnsme = dnsme_domains.main()
print('DNSMadeEasy domains processed.')

master = {}
for domain in ad:   #combining dicts
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

    tmp = []
    for i in range(len(master[domain]['ips'])):
        ip = iptools.parsed_ip(master[domain]['ips'][i])
        if ip.valid:
            master[domain]['subnets'].append(ip.subnet)
            iplist[ip.ipv4] = master[domain]['source']
            tmp.append(ip)
        else:
            master[domain]['ips'].pop(i)
            print('Removed invalid ip: '+ ip.ipv4)
    master[domain]['ips'] = {'private': [], 'public': []}
    for ip in tmp:
        if ip.public:
            master[domain]['ips']['public'].append(ip.ipv4)
        else:
            master[domain]['ips']['private'].append(ip.ipv4)


    for i in range(len(master[domain]['aliases'])): #adding cnames
        alias = master[domain]['aliases'][i]
        if '_wildcard_' in alias:
            master[domain]['aliases'][i] = alias.replace('_wildcard_','*')
        else:
            master[domain]['aliases'][i] = 'https://'+ alias
    

with open('Sources/domains.json','w') as stream:
    stream.write(json.dumps(master, indent=2))

subprocess.run('java -jar c:/saxon/saxon-he-10.3.jar -xsl:dns.xsl -s:Sources/domains.xml')

print('DNS documents done')

import ipdocs
ipdocs.main(iplist)

print('IP documents done')

import ingress2pod
ingress2pod.main()
subprocess.run('java -jar c:/saxon/saxon-he-10.3.jar -xsl:deployments.xsl -s:Sources/kube.xml')

print('Kubernetes documents done')
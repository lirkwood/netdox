import ad_domains
import dnsme_domains
import k8s_domains
import ingress2pod
import iptools

import subprocess
import json
import os
    
print('Removing old documents...')
if not os.path.exists('outgoing'):
    os.mkdir('outgoing')

for path in ('DNS', 'IPs', 'k8s'):
    if not os.path.exists('outgoing/'+path):
        os.mkdir('outgoing/'+path)
    else: 
        for f in os.scandir('outgoing/'+path):
            os.remove(f)
print('Done.')

subprocess.run('pwsh.exe ./get-ad.ps1')
ad = ad_domains.main()
ad_f = ad['forward']
ad_r = ad['reverse']
print('Active Directory domains processed.')
dnsme = dnsme_domains.main()
dnsme_f = dnsme['forward']
dnsme_r = dnsme['reverse']
print('DNSMadeEasy domains processed.')
ingress2pod.main()
k8s = k8s_domains.main()
print('Kubernetes domains processed.')

master = {}
for domain in ad_f:   #combining dicts
    master[domain.lower()] = ad_f[domain]

for domain in dnsme_f:
    if domain in master:
        for ip in dnsme_f[domain]['dest']['ips']:
            master[domain]['dest']['ips'].append(ip)
        for alias in dnsme_f[domain]['dest']['domains']:
            master[domain]['dest']['domains'].append(alias)
    else:
        master[domain] = dnsme_f[domain]

for domain in k8s:
    if domain in master:
        for app in k8s[domain]['dest']['apps']:
            master[domain]['dest']['apps'].append(app)
    else:
        master[domain] = k8s[domain]

ptr = {}    #gathering ptr records
for ip in ad_r:
    ptr[ip] = ad_r[ip]
for ip in dnsme_r:
    if ip in ptr:
        ptr[ip].append(dnsme_r[ip])
    else:
        ptr[ip] = dnsme_r[ip]


iplist = {}
for domain in master:   #adding subnets and sorting public/private ips
    master[domain]['dest']['ips'] = list(dict.fromkeys(master[domain]['dest']['ips']))
    master[domain]['dest']['domains'] = list(dict.fromkeys(master[domain]['dest']['domains']))
    master[domain]['subnets'] = []

    tmp = []
    for i in range(len(master[domain]['dest']['ips'])):
        ip = iptools.parsed_ip(master[domain]['dest']['ips'][i])
        if ip.valid:
            master[domain]['subnets'].append(ip.subnet)
            iplist[ip.ipv4] = master[domain]['source']
            tmp.append(ip)
        else:
            master[domain]['dest']['ips'].pop(i)
            print('Removed invalid ip: '+ ip.ipv4)
    master[domain]['dest']['ips'] = {'private': [], 'public': []}
    for ip in tmp:
        if ip.public:
            master[domain]['dest']['ips']['public'].append(ip.ipv4)
        else:
            master[domain]['dest']['ips']['private'].append(ip.ipv4)


    # for i in range(len(master[domain]['dest']['domains'])): #adding cnames
    #     alias = master[domain]['dest']['domains'][i]
    #     if '_wildcard_' in alias:
    #         master[domain]['dest']['domains'][i] = alias.replace('_wildcard_','*')
    #     else:
    #         master[domain]['dest']['domains'][i] = 'https://'+ alias
    

with open('Sources/dns.json','w') as stream:
    stream.write(json.dumps(master, indent=2))

subprocess.run('java -jar c:/saxon/saxon-he-10.3.jar -xsl:dns.xsl -s:Sources/dns.xml')

print('DNS documents done')

import ipdocs
ipdocs.main(iplist, ptr)

print('IP documents done')

subprocess.run('java -jar c:/saxon/saxon-he-10.3.jar -xsl:deployments.xsl -s:Sources/apps.xml')
subprocess.run('java -jar c:/saxon/saxon-he-10.3.jar -xsl:workers.xsl -s:Sources/workers.xml')
subprocess.run('java -jar c:/saxon/saxon-he-10.3.jar -xsl:clusters.xsl -s:Sources/workers.xml')

print('Kubernetes documents done')
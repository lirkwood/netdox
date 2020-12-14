import os
import csv
import json
from bs4 import BeautifulSoup

import ad_domains
import dnsme_domains
import kube_domains
import subdomains


# To refresh DNSMadeEasy data, uncomment below #
################################################
# import datetime
# import urllib.request
# import hmac
# import hashlib
# import dnsmereq
# dnsmereq.main()
# print('DNSMadeEasy domains retrieved')

# To refresh ActiveDirectory data, uncomment below #
####################################################
# os.system('pwsh.exe ./get-ad.ps1')
# print('Active Directory domains retrieved')

# To refresh Kubernetes data, uncomment below #
###############################################
# os.system('pwsh.exe ./get-ingress.ps1')
# print('Kubernetes domains retrieved')

dnsme_domains.main()
print('DNSMadeEasy domains processed')
ad_domains.main()
print('Active Directory domains processed')
kube_domains.main()
print('Kubernetes domains processed')
subdomains.main()
print('Primary domains extracted')

domains = {}
with open('../sources/domains.csv', 'r') as stream:
    for row in csv.reader(stream):
        d = row[1].lower()
        if d not in domains:
            domains[d] = {}
            domains[d]['ips'] = []
            domains[d]['source'] = row[0]
        for ip in row[2:]:
            domains[d]['ips'].append(ip)



pdomains = []
with open('../Sources/pdomains.txt', 'r') as stream:
    for line in stream:
        pdomains.append(line.strip('\n'))


print('Resolving ".internal" domains')
temp = dict(domains)
for d in temp:
    if d.endswith('.internal'):
        extdomain = d.replace('.internal', '')
        if extdomain not in temp:
            domains[extdomain] = {}
        domains[extdomain]['internal'] = {}
        domains[extdomain]['internal'][d] = temp[d]
        domains.pop(d, None)



def ips(l, soup, s):
    iplist = list(dict.fromkeys(l))
    if s == 'internal':
        ipfrag = soup.find(id='ad_ips')
    else:
        ipfrag = soup.find(id='ips')
    for ip in iplist:
        p = soup.new_tag('property')
        p['datatype'] = 'xref'
        
        if ip.startswith('192.168') or ip.startswith('172') or ip.startswith('10.'):
            p['name'] = 'intip'
            p['title'] = 'Internal IP'
        else:
            p['name'] = 'extip'
            p['title'] = 'External IP'
        ipfrag.append(p)
        
        xref = soup.new_tag('xref')
        xref['frag'] = 'default'
        xref['docid'] = '_nd_' + ip.replace('.', '_')
        p.append(xref)



print('Removing duplicates')
for d in domains:
    docid = '_nd_' + d.replace('.', '_')
    with open('../Hosts/{0}.psml'.format(docid), 'w') as stream:
        with open('../Sources/template-domain.psml', 'r') as template:
            soup = BeautifulSoup(template, features='xml')

            for i in pdomains:
                if d.endswith(i) and d != i:
                    pdomain = '_nd_' + i.replace('.', '_')
                    pdomainraw = i
                    sdomain = d.replace(i, '').strip('.')
                    break
                else:
                    pdomainraw = None
                    pdomain = None
                    sdomain = None

            if 'internal' in domains[d]:
                ad_host = d + '.internal'
            else:
                ad_host = None
                soup.find(id='ad_info').decompose()

            properties = soup.find_all('property')
            for p in properties:
                if p['name'] == 'host':
                    p['value'] = d
                elif p['name'] == 'source':
                    try:
                        p['value'] = domains[d]['source']
                    except KeyError:
                        p['value'] = domains[d]['internal'][ad_host]['source']
                elif p['name'] == 'root':
                    if pdomain:
                        x = soup.new_tag('xref')
                        x['frag'] = 'default'
                        x['docid'] = pdomain
                        x.string = pdomainraw
                        p.append(x)
                    else:
                        p.decompose()
                elif p['name'] == 'subdomain':
                    if sdomain:
                        p['value'] = sdomain
                    else:
                        p.decompose()
                elif p['name'] == 'ad_host':
                    if ad_host:
                        p['value'] = ad_host
                    else:
                        p.decompose()
                
            if 'ips' in domains[d]:
                ips(domains[d]['ips'], soup, 'external')
            if 'internal' in domains[d]:
                ips(domains[d]['internal'][ad_host]['ips'], soup, 'internal')

            soup.uri['docid'] = docid
            soup.uri['title'] = d
            soup.heading.string = d

            stream.write(str(soup))
        

print('Host documents done')

# import ipdocs
# ipdocs.read()

# print('IP documents done')

with open('../Sources/doc_domains.json', 'w') as output:
    output.write(json.dumps(domains, indent=4))
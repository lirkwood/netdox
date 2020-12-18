import os
import csv
import json
from bs4 import BeautifulSoup

import ad_domains
import dnsme_domains
import kube_domains
import subdomains
import binary


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

subndict = binary.netbox_prefixes()

def ips(l, soup, s):
    iplist = list(dict.fromkeys(l))
    subnetlist = []
    if s == 'internal':
        ipfrag = soup.find(id='ad_ipv4')
    else:
        ipfrag = soup.find(id='ipv4')
    for ip in iplist:
        p = soup.new_tag('property')
        p['datatype'] = 'xref'
        
        if ip.startswith('192.168') or ip.startswith('172') or ip.startswith('10.'):
            p['name'] = 'int_ipv4'
            p['title'] = 'Internal IP'
        else:
            p['name'] = 'ext_ipv4'
            p['title'] = 'External IP'
        ipfrag.append(p)

        bin_ip = binary.binaryip(ip)
        for prefix in subndict:
            if bin_ip > subndict[prefix]['lower'] and bin_ip < subndict[prefix]['upper']:
                subnetlist.append(prefix)
                break
        
        xref = soup.new_tag('xref')
        xref['frag'] = 'default'
        xref['docid'] = '_nd_' + ip.replace('.', '_')
        xref['reversetitle'] = p['title'] + ' in fragment ' +  ipfrag['id']
        p.append(xref)



def subnets(l):
    l = list(dict.fromkeys(l))
    subnetfrag = soup.find(id='subnets')
    for subnet in l:
        p = soup.new_tag('property')
        p['name'] = 'subnet'
        p['title'] = 'Subnet'
        p['value'] = subnet
        subnetfrag.append(p)


print('Removing duplicates')
for d in domains:
    docid = '_nd_' + d.replace('.', '_')
    with open('../Hosts/{0}.psml'.format(docid), 'w') as stream:
        with open('../Sources/template-domain.psml', 'r') as template:
            soup = BeautifulSoup(template, features='xml')

            for i in pdomains:
                if d.endswith(i) and d != i:
                    pdomain = i
                    sdomain = d.replace(i, '').strip('.')
                    break
                else:
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
                        p['value'] = pdomain
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

# with open('../Sources/doc_domains.json', 'w') as output:
#     output.write(json.dumps(domains, indent=4))
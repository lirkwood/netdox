import ad_domains
import dnsme_domains
import k8s_domains
import xo_inf
import ingress2pod
import iptools

from bs4 import BeautifulSoup
import subprocess, json, os

os.mkdir('out')
for path in ('DNS', 'IPs', 'k8s', 'xo'):
    os.mkdir('out/'+path)

try:
    print('[INFO][generate.py] Parsing ActiveDirectory response...')
    ad = ad_domains.main()
    ad_f = ad['forward']
    ad_r = ad['reverse']
except Exception as e:
    print('[ERROR][ad_domains.py] ActiveDirectory parsing threw an exception:')
    print(e)
    print('[ERROR][ad_domains.py] ****END****')

try:
    print('[INFO][generate.py] Querying DNSMadeEasy...')
    dnsme = dnsme_domains.main()
    dnsme_f = dnsme['forward']
    dnsme_r = dnsme['reverse']
except Exception as e:
    print('[ERROR][ad_domains.py] DNSMadeEasy query threw an exception:')
    print(e)
    print('[ERROR][ad_domains.py] ****END****')

print('[INFO][generate.py] Parsing DNSMadeEasy response...')

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

try:
    print('[INFO][generate.py] Querying Kubernetes...')
    ingress2pod.main(master)
except Exception as e:
    print('[ERROR][ingress2pod.py] Kubernetes query threw an exception:')
    print(e)
    print('[ERROR][ingress2pod.py] ****END****')

try:
    k8s = k8s_domains.main()
    print('[INFO][generate.py] Parsing Kubernetes response...')
except Exception as e:
    print('[ERROR][k8s_domains.py] Kubernetes parsing threw an exception:')
    print(e)
    print('[ERROR][k8s_domains.py] ****END****')

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


ipdict = {}
for domain in master:   #adding subnets and sorting public/private ips
    master[domain]['dest']['ips'] = list(dict.fromkeys(master[domain]['dest']['ips']))
    master[domain]['dest']['domains'] = list(dict.fromkeys(master[domain]['dest']['domains']))
    master[domain]['subnets'] = []

    tmp = []
    for i in range(len(master[domain]['dest']['ips'])):
        ip = iptools.parsed_ip(master[domain]['dest']['ips'][i])
        if ip.valid:
            master[domain]['subnets'].append(ip.subnet)
            ipdict[ip.ipv4] = {'source': master[domain]['source']}
            tmp.append(ip)
        else:
            master[domain]['dest']['ips'].pop(i)
            print('[WARNING][generate.py] Removed invalid ip: '+ ip.ipv4)
    master[domain]['dest']['ips'] = {'private': [], 'public': []}
    for ip in tmp:
        if ip.public:
            master[domain]['dest']['ips']['public'].append(ip.ipv4)
        else:
            master[domain]['dest']['ips']['private'].append(ip.ipv4)

try:
    print('[INFO][generate.py] Querying Xen Orchestra...')
    xo_inf.main(master)
    print('[INFO][generate.py] Parsing Xen Orchestra response...')
except Exception as e:
    print('[ERROR][xo_inf.py] Xen Orchestra query threw an exception:')
    print(e)
    print('[ERROR][xo_inf.py] ****END****')

    
# search for VMs
for domain in master:
    for ip in master[domain]['dest']['ips']['private']:
        xo_query = subprocess.run(['xo-cli', '--list-objects', 'type=VM', f'mainIpAddress={ip}'], stdout=subprocess.PIPE).stdout
        for vm in json.loads(xo_query):
            master[domain]['dest']['vms'].append(vm['uuid'])



print('[INFO][generate.py] Searching secret server for secrets...')

try:
    import secret_api
    for domain in master:
        master[domain]['secrets'] = {}
        resp = secret_api.searchSecrets(domain, 'URL Key')
        soup = BeautifulSoup(resp.text, features='xml')
        for secret in soup.find_all('SecretSummary'):
            master[domain]['secrets'][secret.SecretId.string] = secret.SecretName.string +';'+ secret.SecretTypeName.string

    with open('src/dns.json','w') as stream:
        stream.write(json.dumps(master, indent=2))
except Exception as e:
    print('[ERROR][secret_api.py] Secret server query threw an exception:')
    print(e)
    print('[ERROR][secret_api.py] ****END****')

try:
    import icinga_inf
    for domain in master:
        master[domain]['icinga'] = 'Not Monitored'
        display_name = icinga_inf.lookup([domain]+[master[domain]['dest']['ips']['private']])
        if display_name:
            master[domain]['icinga'] = display_name
except Exception as e:
    print('[ERROR][icinga_inf.py] Icinga query threw an exception:')
    print(e)
    print('[ERROR][icinga_inf.py] ****END****')


for type in ('ips', 'dns', 'apps', 'workers', 'vms', 'hosts', 'pools'):     #if xsl json import files dont exist, generate them
    if not os.path.exists(f'src/{type}.xml'):
        with open(f'src/{type}.xml','w') as stream:
            stream.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE {type} [
<!ENTITY json SYSTEM "{type}.json">
]>
<{type}>&json;</{type}>""")

xslt = 'java -jar /usr/local/bin/saxon-he-10.3.jar'

subprocess.run(f'{xslt} -xsl:dns.xsl -s:src/dns.xml', shell=True)

print('[INFO][generate.py] DNS documents done')

import ip_inf
ip_inf.main(ipdict, ptr)
subprocess.run(f'{xslt} -xsl:ips.xsl -s:src/ips.xml', shell=True)

print('[INFO][generate.py] IP documents done')

subprocess.run(f'{xslt} -xsl:clusters.xsl -s:src/workers.xml', shell=True)
subprocess.run(f'{xslt} -xsl:workers.xsl -s:src/workers.xml', shell=True)
subprocess.run(f'{xslt} -xsl:apps.xsl -s:src/apps.xml', shell=True)

print('[INFO][generate.py] Kubernetes documents done')

subprocess.run(f'{xslt} -xsl:pools.xsl -s:src/pools.xml', shell=True)
subprocess.run(f'{xslt} -xsl:hosts.xsl -s:src/hosts.xml', shell=True)
subprocess.run(f'{xslt} -xsl:vms.xsl -s:src/vms.xml', shell=True)

print('[INFO][generate.py] Xen Orchestra documents done')
print('[INFO][generate.py] Testing domains...')
try:
    import linktools
    linktools.main()
except Exception as e:
    print('[ERROR][linktools.py] Link test and screenshot compare module threw an exception:')
    print(e)
    print('[ERROR][linktools.py] ****END****')

# load pageseeder properties and auth info
with open('pageseeder.properties','r') as f: properties = f.read()
with open('src/authentication.json','r') as f:
    auth = json.load(f)['pageseeder']

# if property is defined in authentication.json use that value
with open('pageseeder.properties','w') as stream:
    for line in properties.splitlines():
        property = line.split('=')[0]
        if property in auth:
            stream.write(f'{property}={auth[property]}')
        else:
            stream.write(line)
        stream.write('\n')

subprocess.run('bash -c "cd /opt/app/out && zip -r -q netdox-src.zip * && cd /opt/app && ant -lib /opt/ant/lib"', shell=True)
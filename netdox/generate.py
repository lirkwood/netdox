import ad_domains
import dnsme_domains
import k8s_domains
import iptools, utils

from bs4 import BeautifulSoup
import subprocess, json, os

os.mkdir('out')
for path in ('DNS', 'IPs', 'k8s', 'xo', 'screenshots', 'review'):
    os.mkdir('out/'+path)

def integrate(dns_set, superset):
    """
    Integrates some set of dns records into a master set
    """
    for domain in dns_set:
        if domain not in superset:
            superset[domain] = dns_set[domain]
        else:
            superset[domain] = utils.merge(superset[domain], dns_set[domain])



#####################
# Gathering domains #
#####################

# Main set of DNS records, dns_obj.name: dns_obj
master = {}

try:
    print('[INFO][generate.py] Parsing ActiveDirectory response...')
    ad = ad_domains.main()
    ad_f = ad['forward']
    ad_r = ad['reverse']
except Exception as e:
    print('[ERROR][ad_domains.py] ActiveDirectory parsing threw an exception:')
    raise e

try:
    print('[INFO][generate.py] Querying DNSMadeEasy...')
    dnsme = dnsme_domains.main()
    dnsme_f = dnsme['forward']
    dnsme_r = dnsme['reverse']
except Exception as e:
    print('[ERROR][ad_domains.py] DNSMadeEasy query threw an exception:')
    raise e

print('[INFO][generate.py] Parsing DNSMadeEasy response...')

# combine activedirectory and dnsmadeeasy data

for source in (ad_f, dnsme_f):
    integrate(source, master)
    del source

# Api call getting all vms/hosts/pools
try:
    import xo_inf
    print('[INFO][generate.py] Querying Xen Orchestra...')
    xo_inf.main(master)
    print('[INFO][generate.py] Parsing Xen Orchestra response...')
except Exception as e:
    print('[ERROR][xo_inf.py] Xen Orchestra query threw an exception:')
    raise e


# maps apps to domains by tracing back through pods/services/ingress
try:
    import k8s_inf_new
    print('[INFO][generate.py] Querying Kubernetes...')
    k8s_inf_new.main()
except Exception as e:
    print('[ERROR][k8s_inf.py] Kubernetes query threw an exception:')
    raise e

# gets kubernetes internal dns info
try:
    integrate(k8s_domains.main(), master)
    print('[INFO][generate.py] Parsing Kubernetes response...')
except Exception as e:
    print('[ERROR][k8s_domains.py] Kubernetes parsing threw an exception:')
    raise e



try:
    # Remove manually excluded domains once all dns sources have been queried
    with open('src/exclusions.txt','r') as stream:
        exclusions = stream.read().splitlines()
except FileNotFoundError:
    print('[INFO][generate.py] No exclusions.txt detected. All domains will be included.')
else:
    tmp = []
    for domain in master:
        if domain in exclusions:
            tmp.append(domain)
    for domain in tmp:
        del master[domain]


ptr = {}    #gathering ptr records
for ip in ad_r:
    ptr[ip] = ad_r[ip]
for ip in dnsme_r:
    if ip in ptr:
        ptr[ip].append(dnsme_r[ip])
    else:
        ptr[ip] = dnsme_r[ip]

# generate json file with all ptr records in the dns
ipdict = {}
for dns in master:
    for ip in master[dns].ips:
        ipdict[ip] = {'source': master[dns].source}


# not literally ptr records, forward dns records reversed for convenience
ptr_implied = {}
for dns in master:
    for ip in master[dns].ips:
        if ip not in ptr_implied:
            ptr_implied[ip] = []
        ptr_implied[ip].append(dns)


########################
# Gathering other data #
########################

# check each ip for each domain against the NAT
try:
    import nat_inf
    for dns in master:
        for ip in master[dns].ips:
            ip_alias = nat_inf.lookup(ip)
            if ip_alias and (ip_alias in ptr_implied):
                for _dns in ptr_implied[ip_alias]:
                    if _dns != dns:
                        master[dns].link(_dns, 'nat')
except Exception as e:
    print('[ERROR][nat_inf.py] NAT mapping threw an exception:')
    print(e)    # Non essential => continue without
    print('[ERROR][nat_inf.py] ****END****')


# search for VMs to match on domains
for dns in master:
    for ip in master[dns].private_ips:
        xo_query = subprocess.run(['xo-cli', '--list-objects', 'type=VM', f'mainIpAddress={ip}'], stdout=subprocess.PIPE).stdout
        for vm in json.loads(xo_query):
            master[dns].link(vm['uuid'], 'vm')

# Add name of domain in icinga if it exists
print('[INFO][generate.py] Querying Icinga...')
try:
    import icinga_inf
    for dns in master:
        master[dns].icinga = 'Not Monitored'
        # search icinga for objects with address == domain (or any private ip for that domain)
        details = icinga_inf.lookup([dns] + list(master[dns].private_ips))
        if details:
            master[dns].icinga = details['display_name']
except Exception as e:
    print('[ERROR][icinga_inf.py] Icinga query threw an exception:')
    print(e)
    print('[ERROR][icinga_inf.py] ****END****')

print('[INFO][generate.py] Searching for pageseeder licenses...')
try:
    import license_inf
    licenses = license_inf.fetch(master)
    for license_id in licenses:
        for domain in licenses[license_id]:
            if isinstance(domain, str) and not (domain.startswith('[old]') or domain.startswith('[ext]')):
                master[domain].license = license_id
except Exception as e:
    print('[ERROR][license_inf.py] License processing threw an exception:')
    print(e)
    print('[ERROR][license_inf.py] ****END****')


############################
# Applying document labels #
############################

print('[INFO][generate.py] Applying document labels...')
for domain in master:
    master[domain].labels = []
    # Icinga
    if master[domain].icinga == 'Not Monitored':
        master[domain].labels.append('icinga_not_monitored')


################################################
# Data gathering done, start generating output #
################################################

with open('src/dns.json','w') as dns:
    dns.write(json.dumps(master, cls=utils.JSONEncoder, indent=2))

    
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
    subprocess.run('node screenshotCompare.js', shell=True)
except Exception as e:
    print('[ERROR][screenshotCompare.js] Screenshot compare module threw an exception:')
    print(e)
    print('[ERROR][screenshotCompare.js] ****END****')

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

with open('build.xml','r') as stream: soup = BeautifulSoup(stream, features='xml')
with open('build.xml','w') as stream:
    soup.find('ps:upload')['group'] = auth['group']
    stream.write(soup.prettify().split('\n',1)[1]) # remove first line of string as xml declaration


subprocess.run(f'{xslt} -xsl:status.xsl -s:src/review.xml -o:out/status_update.psml', shell=True)
print('[INFO][generate.py] Status update generated')

import cleanup
cleanup.clean()

subprocess.run('bash -c "cd /opt/app/out && zip -r -q netdox-src.zip * && cd /opt/app && ant -lib /opt/ant/lib"', shell=True)
print('[INFO][generate.py] Pageseeder upload finished')

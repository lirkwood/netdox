import ad_domains, dnsme_domains, k8s_domains
import k8s_inf_new, ip_inf, xo_inf, nat_inf, icinga_inf, license_inf
import cleanup, utils

import subprocess, json, os
from bs4 import BeautifulSoup

@utils.critical
def init():
    """
    Creates dirs and template files, loads authentication data, excluded domains, etc...
    """
    # Put this in init.sh
    os.mkdir('out')
    for path in ('DNS', 'IPs', 'k8s', 'xo', 'screenshots', 'review'):
        os.mkdir('out/'+path)
    
    # Use set template function for this before each call
    for type in ('ips', 'dns', 'apps', 'workers', 'vms', 'hosts', 'pools'):     #if xsl json import files dont exist, generate them
        with open(f'src/{type}.xml','w') as stream:
            stream.write(f"""<?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE {type} [
            <!ENTITY json SYSTEM "{type}.json">
            ]>
            <{type}>&json;</{type}>""")

    # load pageseeder properties and auth info
    with open('pageseeder.properties','r') as f: 
        psproperties = f.read()
    with open('src/authentication.json','r') as f:
        auth = json.load(f)
        psauth = auth['pageseeder']

    # overwrite ps properties with external values
    with open('pageseeder.properties','w') as stream:
        for line in psproperties.splitlines():
            property = line.split('=')[0]
            if property in psauth:
                stream.write(f'{property}={psauth[property]}')
            else:
                stream.write(line)
            stream.write('\n')

    # Specify ps group in Ant build.xml
    with open('build.xml','r') as stream: 
        soup = BeautifulSoup(stream, features='xml')
    with open('build.xml','w') as stream:
        soup.find('ps:upload')['group'] = psauth['group']
        stream.write(soup.prettify().split('\n',1)[1]) # remove first line of string as xml declaration

    try:
    # Remove manually excluded domains once all dns sources have been queried
        with open('src/exclusions.txt','r') as stream:
            global exclusions
            exclusions = stream.read().splitlines()
    except FileNotFoundError:
        print('[INFO][generate.py] No exclusions.txt detected. All domains will be included.')

#####################
# Gathering domains #
#####################

@utils.critical
def integrate(dns_set, superset):
    """
    Integrates some set of dns records into a master set
    """
    for domain in dns_set:
        if domain not in superset:
            superset[domain] = dns_set[domain]
        else:
            superset[domain] = utils.merge_sets(superset[domain], dns_set[domain])

@utils.handle
def nat(dns_set):
    """
    Integrates IPs from NAT into a dns set
    """
    for dns in dns_set:
        for ip in dns_set[dns].ips:
            ip_alias = nat_inf.lookup(ip)
            if ip_alias:
                dns_set[dns].link(ip_alias, 'ipv4')

    return dns_set

@utils.handle
def xo_vms(dns_set):
    for dns in dns_set:
        for ip in dns_set[dns].private_ips:
            xo_query = subprocess.run(['xo-cli', '--list-objects', 'type=VM', f'mainIpAddress={ip}'], stdout=subprocess.PIPE).stdout
            for vm in json.loads(xo_query):
                dns_set[dns].link(vm['uuid'], 'vm')

@utils.handle
def icinga_labels(dns_set):
    """
    Integrates icinga display labels into a dns set
    """
    for dns in dns_set:
        # search icinga for objects with address == domain (or any private ip for that domain)
        details = icinga_inf.lookup([dns] + list(dns_set[dns].private_ips))
        if details:
            dns_set[dns].icinga = details['display_name']
    return dns_set

@utils.handle
def license_keys(dns_set):
    """
    Integrates license keys into a dns set
    """
    licenses = license_inf.fetch(dns_set)
    for license_id in licenses:
        for domain in licenses[license_id]:
            if isinstance(domain, str) and not (domain.startswith('[old]') or domain.startswith('[ext]')):
                dns_set[domain].license = license_id
    return dns_set


## All queries called from here
@utils.critical
def queries():
    """
    Makes all queries and returns complete dns set
    """
    # Main set of DNS records, dns_obj.name: dns_obj
    master = {}

    # DNS queries
    ad_f, ad_r = utils.handle(ad_domains.main)()
    dnsme_f, dnsme_r = utils.handle(dnsme_domains.main)()

    for source in (ad_f, dnsme_f):
        integrate(source, master)
        del source

    # Integrate NAT
    master = nat(master)

    # VM/App queries
    utils.handle(xo_inf.main)(master)
    utils.handle(k8s_inf_new.main)()

    # More DNS (move this)
    k8s = utils.handle(k8s_domains.main)()
    integrate(k8s, master)

    # Exclude specified domains
    for domain in exclusions:
        try:
            del master[domain]
        except KeyError:
            pass

    ptr = {}
    for ip in ad_r:
        ptr[ip] = ad_r[ip]
    for ip in dnsme_r:
        if ip in ptr:
            ptr[ip].append(dnsme_r[ip])
        else:
            ptr[ip] = dnsme_r[ip]

    # Describes source ips came from
    ipsources = {}
    for dns in master:
        for ip in master[dns].ips:
            ipsources[ip] = {'source': master[dns].source}

    return (master, ptr, ipsources)


@utils.handle
def labels(dns_set):
    """
    Applies any relevant document labels
    """
    for dns in dns_set:
        dns_set[dns].labels = []
        # Icinga
        if not dns_set[dns].icinga:
            dns_set[dns].labels.append('icinga_not_monitored')

@utils.critical
def write_dns(dns_set):
    """
    Encodes dns set as json and writes to file
    """
    jsondata = {}
    for dns in dns_set:
        jsondata[dns] = dns_set[dns].__dict__
    with open('src/dns.json','w') as dns:
        dns.write(json.dumps(jsondata, cls=utils.JSONEncoder, indent=2))
    del jsondata

@utils.critical
def xslt(xsl, src, out=None):
    xsltpath = 'java -jar /usr/local/bin/saxon-he-10.3.jar'
    if out:
        subprocess.run(f'{xsltpath} -xsl:{xsl} -s:{src} -o:{out}', shell=True)
    else:
        subprocess.run(f'{xsltpath} -xsl:{xsl} -s:{src}', shell=True)

@utils.handle
def screenshots():
    subprocess.run('node screenshotCompare.js', shell=True)
    xslt('status.xsl', 'src/review.xml', 'out/status_update.psml')


def main():
    init()

    master, ptr, ipsources = queries()
    master = labels(master)

    master = xo_vms(master)
    master = icinga_labels(master)
    master = license_keys(master)

    utils.handle(ip_inf.main)(ipsources, ptr)
    screenshots()

    # Write DNS documents
    xslt('dns.xsl', 'src/dns.xml')
    # Write IP documents
    xslt('ips.xsl', 'src/ips.xml')
    # Write K8s documents
    xslt('clusters.xsl', 'src/workers.xml')
    xslt('workers.xsl', 'src/workers.xml')
    xslt('apps.xsl', 'src/apps.xml')
    # Write XO documents
    xslt('pools.xsl', 'src/pools.xml')
    xslt('hosts.xsl', 'src/hosts.xml')
    xslt('vms.xsl', 'src/vms.xml')

    utils.handle(cleanup.clean)()


if __name__ == '__main__':
    main()
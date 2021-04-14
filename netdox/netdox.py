import ad_domains, dnsme_domains, k8s_domains
import k8s_inf, ip_inf, xo_inf, nat_inf, icinga_inf, license_inf
import cleanup, utils

import subprocess, json, os
from bs4 import BeautifulSoup


##################
# Initialisation #
##################

@utils.critical
def init():
    """
    Creates dirs and template files, loads authentication data, excluded domains, etc...
    """
    # Put this in init.sh
    os.mkdir('out')
    for path in ('DNS', 'IPs', 'k8s', 'xo', 'screenshots', 'screenshot_history', 'review'):
        os.mkdir('out/'+path)
    
    for type in ('ips', 'dns', 'apps', 'workers', 'vms', 'hosts', 'pools', 'review'):
        with open(f'src/{type}.xml','w') as stream:
            stream.write(f"""<?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE {type} [
            <!ENTITY json SYSTEM "{type}.json">
            ]>
            <{type}>&json;</{type}>""")

    # load pageseeder properties and auth info
    with open('src/pageseeder.properties','r') as f: 
        psproperties = f.read()
    with open('src/authentication.json','r') as f:
        auth = json.load(f)
        psauth = auth['pageseeder']

    # overwrite ps properties with external values
    with open('src/pageseeder.properties','w') as stream:
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
            exclusions = stream.read().splitlines()
    except FileNotFoundError:
        print('[INFO][generate.py] No exclusions.txt detected. All domains will be included.')

    return exclusions


######################
# Gathering DNS info #
######################

@utils.critical
def integrate(dns_set, superset):
    """
    Integrates some set of dns records into a master set
    """
    for domain in dns_set:
        dns = dns_set[domain]
        if domain not in superset:
            superset[dns.name] = dns
        else:
            superset[domain] = utils.merge_sets(superset[domain], dns_set[domain])

## All queries called from here
@utils.critical
def queries():
    """
    Makes all queries and returns complete dns set
    """
    # Main set of DNS records, dns_obj.name: dns_obj
    master = {}

    # DNS queries
    ad_f, ad_r = ad_domains.main()
    dnsme_f, dnsme_r = dnsme_domains.main()

    for source in (ad_f, dnsme_f):
        integrate(source, master)
        del source

    # VM/App queries
    xo_inf.main(master)
    k8s_inf.main()

    # More DNS (move this)
    k8s = k8s_domains.main()
    integrate(k8s, master)

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


###########################
# Non-essential functions #
###########################

@utils.handle
def nat(dns_set):
    """
    Integrates IPs from NAT into a dns set
    """
    for domain in dns_set:
        dns = dns_set[domain]
        for ip in dns.ips:
            ip_alias = nat_inf.lookup(ip)
            if ip_alias:
                dns.link(ip_alias, 'ipv4')

    return dns_set

@utils.handle
def xo_vms(dns_set):
    """
    Links domains to Xen Orchestra VMs with the same IP
    """
    with open('src/vms.json', 'r') as stream:
        vms = json.load(stream)
        for domain in dns_set:
            dns = dns_set[domain]
            for vm in vms:
                try:
                    if vm['mainIpAddress'] in dns.ips:
                        dns.link(vm['uuid'], 'vm')
                except KeyError:
                    pass
    return dns_set

@utils.handle
def icinga_labels(dns_set):
    """
    Integrates icinga display labels into a dns set
    """
    for domain in dns_set:
        dns = dns_set[domain]
        # search icinga for objects with address == domain (or any private ip for that domain)
        details = icinga_inf.lookup([domain] + list(dns.private_ips))
        if details:
            dns.icinga = details['display_name']
        else:
            for alias in dns.domains:
                if (alias in dns_set) and ('icinga' in dns_set[alias].__dict__):
                    dns.icinga = dns_set[alias].icinga
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

@utils.handle
def license_orgs(dns_set):
    """
    Integrates organisations into a dns set inferred from associated license
    """
    for domain in dns_set:
        dns = dns_set[domain]
        if 'license' in dns.__dict__:
            org_id = license_inf.org(dns.license)
            if org_id:
                dns.org = org_id
    return dns_set

@utils.handle
def labels(dns_set):
    """
    Applies any relevant document labels
    """
    # for domain in dns_set:
    #     dns = dns_set[domain]
    #     dns.labels = []
    #     # Icinga
    #     if 'icinga' in dns.__dict__:
    #         dns.labels.append('icinga_not_monitored')
    return dns_set

@utils.handle
def exclude(dns_set, domain_set):
    """
    Removes dns records with names in some set from some dns set
    """
    for domain in domain_set:
        try:
            del dns_set[domain]
        except KeyError:
            pass
    return dns_set

#############################
# Writing data to json/psml #
#############################

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
    """
    Runs some xslt using Saxon
    """
    xsltpath = 'java -jar /usr/local/bin/saxon-he-10.3.jar'
    if out:
        subprocess.run(f'{xsltpath} -xsl:{xsl} -s:{src} -o:{out}', shell=True)
    else:
        subprocess.run(f'{xsltpath} -xsl:{xsl} -s:{src}', shell=True)


##################
# Imgdiff script #
##################

@utils.critical
def screenshots():
    """
    Runs screenshotCompare node.js script and writes output using xslt
    """
    subprocess.run('node screenshotCompare.js', check=True, shell=True)
    xslt('status.xsl', 'src/review.xml', 'out/status_update.psml')


#############
# Main flow #
#############

def main():
    exclusions = init()

    master, ptr, ipsources = queries()
    master = exclude(master, exclusions)
    master = nat(master)
    master = xo_vms(master)
    master = icinga_labels(master)
    master = license_keys(master)
    master = license_orgs(master)
    master = labels(master)
    write_dns(master)

    # Write DNS documents
    xslt('dns.xsl', 'src/dns.xml')
    # Write IP documents
    ip_inf.main(ipsources, ptr)
    xslt('ips.xsl', 'src/ips.xml')
    # Write K8s documents
    xslt('clusters.xsl', 'src/workers.xml')
    xslt('workers.xsl', 'src/workers.xml')
    xslt('apps.xsl', 'src/apps.xml')
    # Write XO documents
    xslt('pools.xsl', 'src/pools.xml')
    xslt('hosts.xsl', 'src/hosts.xml')
    xslt('vms.xsl', 'src/vms.xml')

    screenshots()
    cleanup.clean()


if __name__ == '__main__':
    main()
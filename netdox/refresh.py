import ad_api, dnsme_api, cf_domains, k8s_domains   # dns query scripts
import k8s_inf, xo_api, nat_inf, icinga_inf, license_inf   # other info
import cleanup, ansible, iptools, utils   # utility scripts

import subprocess, boto3, json


######################
# Gathering DNS info #
######################

@utils.handle
def integrate(superset, dns_set):
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
    # Main sets of DNS records, dns_obj.name: dns_obj
    forward = {}
    reverse = {}

    # DNS queries
    ad_f, ad_r = ad_api.fetchDNS()
    dnsme_f, dnsme_r = dnsme_api.fetchDNS()
    cf_f, cf_r = cf_domains.main()

    for source in (ad_f, dnsme_f, cf_f):
        integrate(forward, source)
        del source
    for source in (ad_r, dnsme_r, cf_r):
        integrate(reverse, source)
        del source

    # VM/App/AWS queries
    xo_api.fetchObjects(forward)
    k8s_inf.main()
    aws_inf()

    # More DNS (move this)
    k8s = k8s_domains.main()
    integrate(forward, k8s)

    return (forward, reverse)


@utils.critical
def ips(forward, reverse):
    """
    Assembles unique set of all ips referenced in the dns and writes it
    """
    subnets = set()
    for domain in forward:
        dns = forward[domain]
        for ip in dns.ips:
            if ip not in reverse:
                reverse[ip] = utils.ptr(ip, source=dns.source)
            if not iptools.public_ip(ip):
                subnets.add(reverse[ip].subnet)
    
    for subnet in subnets:
        for ip in iptools.subn_iter(subnet):
            if ip not in reverse:
                reverse[ip] = utils.ptr(ip, source='Generated', unused=True)

    write_dns(reverse, 'ips')

@utils.critical
def aws_inf():
    client = boto3.client('ec2')
    instances = client.describe_instances()
    write_dns(instances, 'aws')

###########################
# Non-essential functions #
###########################

@utils.handle
def exclude(dns_set):
    """
    Removes dns records with names in some set from some dns set
    """
    with open('src/exclusions.json', 'r') as stream:
        domain_set = json.load(stream)['dns']
    for domain in domain_set:
        try:
            del dns_set[domain]
        except KeyError:
            pass

@utils.handle
def nat(dns_set):
    """
    Integrates IPs from NAT into a dns set
    """
    nat_inf.pfsense()
    for domain in dns_set:
        dns = dns_set[domain]
        for ip in dns.ips:
            ip_alias = nat_inf.lookup(ip)
            if ip_alias:
                dns.link(ip_alias, 'ipv4')

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

@utils.handle
def aws_ec2(dns_set):
    """
    Links domains to AWS EC2 instances with the same IP
    """
    with open('src/aws.json', 'r') as stream:
        reservations = json.load(stream)
        for domain in dns_set:
            dns = dns_set[domain]
            for instances in reservations:
                for instance in instances:
                    if instance['PrivateIpAddress'] in dns.ips or instance['PublicIpAddress'] in dns.ips:
                        dns.link(instance['InstanceId'], 'ec2')

@utils.handle
def icinga_services(dns_set):
    """
    Integrates icinga display labels into a dns set
    """
    objects = icinga_inf.fetchObjects()
    for domain in dns_set:
        dns = dns_set[domain]
        # search icinga for objects with address == domain (or any private ip for that domain)
        for selector in [domain] + list(dns.ips):
            for icinga_host in objects:
                if selector in objects[icinga_host]:
                    if icinga_host not in dns.icinga:
                        dns.icinga[icinga_host] = {}
                    dns.icinga[icinga_host] = objects[icinga_host][selector] | dns.icinga[icinga_host]

        if not dns.icinga:
            ansible.icinga_add_generic(domain, location=dns.location)

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

#############################
# Writing data to json/psml #
#############################

@utils.critical
def write_dns(dns_set, name='dns'):
    """
    Writes dns set to json file
    """
    with open(f'src/{name}.json', 'w') as dns:
        dns.write(json.dumps(dns_set, cls=utils.JSONEncoder, indent=2))


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
    # get dns info
    forward, reverse = queries()

    # apply additional info/filters
    exclude(forward)
    nat(forward)
    xo_vms(forward)
    aws_ec2(forward)
    icinga_services(forward)
    license_keys(forward)
    license_orgs(forward)
    labels(forward)

    write_dns(forward)

    # Write DNS documents
    xslt('dns.xsl', 'src/dns.xml')
    # Write IP documents
    ips(forward, reverse)
    xslt('ips.xsl', 'src/ips.xml')
    # Write K8s documents
    xslt('clusters.xsl', 'src/workers.xml')
    xslt('workers.xsl', 'src/workers.xml')
    xslt('apps.xsl', 'src/apps.xml')
    # Write XO documents
    xslt('pools.xsl', 'src/pools.xml')
    xslt('hosts.xsl', 'src/hosts.xml')
    xslt('vms.xsl', 'src/vms.xml')
    # Write AWS documents
    xslt('aws.xsl', 'src/aws.xml')

    screenshots()
    cleanup.clean()


if __name__ == '__main__':
    main()
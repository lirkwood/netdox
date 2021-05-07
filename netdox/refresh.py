import ps_api, ad_api, cf_domains, k8s_domains, dnsme_api   # dns query scripts
import k8s_inf, xo_api, nat_inf, icinga_inf, license_inf   # other info
import cleanup, iptools, utils   # utility scripts

import subprocess, asyncio, shutil, boto3, json, os
from bs4 import BeautifulSoup

##################
# Initialisation #
##################

@utils.critical
def init():
    """
    Some init commands to run every time the DNS data is refreshed
    """
    # remove old output files
    for folder in os.scandir('out'):
        if folder.is_dir():
            for file in os.scandir(folder):
                if file.is_file():
                    os.remove(file)
                else:
                    shutil.rmtree(file)
        else:
            os.remove(folder)

    # load dns roles
    config = {
        "website": [],
        "storage": [],
        "pageseeder": [],
        "unmonitored": [],
        "exclude": []
    }
    configSoup = BeautifulSoup(ps_api.get_fragment('_nd_config', '2'), features='xml')
    for para in configSoup("para"):
        if para.inline and hasattr(para.inline, 'label'):
            try:
                config[para.inline['label']].append(para.inline.string)
            except KeyError:
                print(f'[WARNING][init.py] Unknown DNS role {para.inline["label"]}')
            except AttributeError:
                print(f'[WARNING][init.py] Malformed role specification in config document.')

    with open('src/config.json', 'w') as stream:
        stream.write(json.dumps(config, indent=2))


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
    asyncio.run(xo_api.fetchObjects(forward))
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
def apply_roles(dns_set):
    """
    Applies custom roles defined in _nd_config
    """
    with open('src/config.json', 'r') as stream:
        config = json.load(stream)
    excluded = []
    for domain in dns_set:
        for role in config:
            if domain in config[role]:
                dns_set[domain].role = role
                if role == 'exclude':
                    excluded.append(domain)

    for domain in excluded:
        if domain in dns_set:
            del dns_set[domain]

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
            for uuid in vms:
                vm = vms[uuid]
                try:
                    if vm['mainIpAddress'] in dns.ips:
                        dns.link(uuid, 'vm')
                except KeyError:
                    pass

@utils.handle
def aws_ec2(dns_set):
    """
    Links domains to AWS EC2 instances with the same IP
    """
    with open('src/aws.json', 'r') as stream:
        aws = json.load(stream)
        for domain in dns_set:
            dns = dns_set[domain]
            for reservation in aws['Reservations']:
                for instance in reservation['Instances']:
                    if instance['PrivateIpAddress'] in dns.ips or instance['PublicIpAddress'] in dns.ips:
                        dns.link(instance['InstanceId'], 'ec2')

@utils.handle
def icinga_services(dns_set):
    icinga_inf.objectsByDomain()
    tmp = {}
    for domain in dns_set:
        dns = dns_set[domain]
        # search icinga for objects with address == domain (or any ip for that domain)
        if not icinga_inf.dnsLookup(dns):
            tmp[domain] = dns
    # if some objects had invalid monitors, refresh and retest.
    if tmp: icinga_services(tmp)

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


#####################################
# Generating config files for users #
#####################################

@utils.handle
@xo_api.authenticate
async def template_map():
    """
    Generates json with all vms/snapshots/templates
    """
    vmSource = {
        'vms': {},
        'snapshots': {},
        'templates': {}
    }
    vms = await xo_api.fetchType('VM')
    templates = await xo_api.fetchType('VM-template')
    snapshots = await xo_api.fetchType('VM-snapshot')

    for vm in vms:
        name = vms[vm]['name_label']
        vmSource['vms'][name] = vm

    for snapshot in snapshots:
        name = snapshots[snapshot]['name_label']
        vmSource['snapshots'][name] = snapshot
        
    for template in templates:
        name = templates[template]['name_label']
        vmSource['templates'][name] = template

    with open('src/templates.json', 'w', encoding='utf-8') as stream:
        stream.write(json.dumps(vmSource, indent=2, ensure_ascii=False))
    xslt('templates.xsl', 'src/templates.xml', 'out/config/templates.psml')
    

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
    # get dns info
    forward, reverse = queries()

    # apply additional modifications/filters
    apply_roles(forward)
    nat(forward)
    xo_vms(forward)
    aws_ec2(forward)
    icinga_services(forward)
    license_keys(forward)
    license_orgs(forward)
    labels(forward)

    # gather config data (XO templates etc.)
    asyncio.run(template_map())

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
    init()
    main()
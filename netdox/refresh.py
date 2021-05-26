import pluginmaster, license_inf, cleanup, iptools, ps_api, utils   # utility scripts
import subprocess, shutil, json, os
from distutils.util import strtobool
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

    #Initialise plugins
    pluginmaster.initPlugins()

    # load dns config from pageseeder
    config = {"exclusions": []}
    psConfigInf = json.loads(ps_api.get_uri('_nd_config'))
    if psConfigInf['title'] == 'DNS Config':
        # load roles
        roleFrag = BeautifulSoup(ps_api.get_fragment('_nd_config', 'roles'), features='xml')
        for xref in roleFrag("xref"):
            roleConfig = ps_api.pfrag2dict(ps_api.get_fragment(xref['docid'], 'config'))
            # load domains with this role
            domains = []
            revXrefs = BeautifulSoup(ps_api.get_xrefs(xref['docid']), features='xml')
            for revXref in revXrefs("reversexref"):
                if 'documenttype' in revXref.attrs and revXref['documenttype'] == 'dns':
                    domains.append(revXref['urititle'])
            
            roleName = roleConfig['name']
            screenshot = strtobool(roleConfig['screenshot'])
            del roleConfig['name'], roleConfig['screenshot']
            
            config[roleName] = (roleConfig | {
                "screenshot": screenshot,
                "domains": domains
            })

        # load exclusions
        exclusionSoup = BeautifulSoup(ps_api.get_fragment('_nd_config', 'exclude'), features='xml')
        for para in exclusionSoup("para"):
            config['exclusions'].append(para.string)

        # load batch defined roles
        try:
            with open('src/roles.json', 'r') as stream:
                roles = json.load(stream)
        except FileNotFoundError:
            pass
        else:
            for role in roles:
                if role in config:
                    print(f'[INFO][refresh.py] Loaded additional data for role {role} from roles.json')
                    config[role]['domains'] += roles[role]

        with open('src/config.json', 'w') as stream:
            stream.write(json.dumps(config, indent=2))
    else:
        # make defaultconfig
        for file in os.scandir('src/defconf'):
            shutil.copyfile(file, f'out/config/{file}')
    
    utils.loadConfig()


######################
# Critical functions #
######################

@utils.critical
def flatten(dns_set: dict[str, utils.DNSRecord]):
    for domain in dns_set:
        if (domain.lower() in dns_set) and (dns_set[domain.lower()] is not dns_set[domain]):
            union = utils.merge_sets(dns_set[domain.lower()], dns_set[domain])
            del dns_set[domain]
            dns_set[domain.lower()] = union

@utils.critical
def apply_roles(dns_set: dict[str, utils.DNSRecord]):
    """
    Applies custom roles defined in _nd_config
    """
    config = utils.config

    for domain in config['exclusions']:
        try:
            del dns_set[domain]
        except KeyError: pass
    
    unassigned = list(dns_set.keys())
    for role in config.keys():
        if role != 'exclusions':
            for domain in config[role]['domains']:
                try:
                    dns_set[domain].role = role
                    try:
                        unassigned.remove(domain)
                    except ValueError:
                        print(f'[WARNING][refresh.py] {domain} is present multiple times in config')
                except KeyError:
                    pass
    
    for domain in unassigned:
        try:
            dns_set[domain].role = 'default'
            config['default']['domains'].append(domain)
        except KeyError:
            print('[DEBUG][refresh.py] Unexpected behaviour: dns_set is missing domain in unassigned')

@utils.critical
def ips(forward: dict[str, utils.DNSRecord], reverse: dict[str, utils.PTRRecord]):
    """
    Populates a reverse dns set with any missing IPs from a forward dns set
    """
    subnets = set()
    for domain in forward:
        dns = forward[domain]
        for ip in dns.ips:
            if ip not in reverse:
                reverse[ip] = utils.PTRRecord(ip)
            if not iptools.public_ip(ip):
                subnets.add(reverse[ip].subnet)
    
    for subnet in subnets:
        for ip in iptools.subn_iter(subnet):
            if ip not in reverse:
                reverse[ip] = utils.PTRRecord(ip, unused=True)

@utils.critical
def screenshots():
    """
    Runs screenshotCompare node.js script and writes output using xslt
    """
    subprocess.run('node screenshotCompare.js', check=True, shell=True)
    utils.xslt('status.xsl', 'src/review.xml', 'out/status_update.psml')


###########################
# Non-essential functions #
###########################

@utils.handle
def locations(dns_set: dict[str, utils.DNSRecord]):
    unlocated = []
    for domain, dns in dns_set.items():
        if not dns.location:
            for alias in dns.cnames:
                try:
                    if dns_set[alias].location:
                        dns.location = dns_set[alias].location
                except KeyError:
                    pass
        
        if not dns.location:
            unlocated.append(domain)
    if unlocated:
        print('[WARNING][refresh] Some records are missing location data. For a complete list see /var/log/unlocated.json')
        with open('/var/log/unlocated.json', 'w') as stream:
            stream.write(json.dumps(unlocated, indent=2))

@utils.handle
def license_keys(dns_set: dict[str, utils.DNSRecord]):
    """
    Integrates license keys into a dns set
    """
    licenses = license_inf.fetch()
    for domain in licenses:
        if domain in dns_set:
            dns = dns_set[domain]
            dns.license = licenses[domain]
            if dns.role != 'pageseeder':
                print(f'[WARNING][refresh.py] {dns.name} has a PageSeeder license but is using role {dns.role}')

@utils.handle
def license_orgs(dns_set: dict[str, utils.DNSRecord]):
    """
    Integrates organisations into a dns set inferred from associated license
    """
    for domain, dns in dns_set.items():
        if 'license' in dns.__dict__:
            org_id = license_inf.org(dns.license)
            if org_id:
                dns.org = org_id

@utils.handle
def labels(dns_set: dict[str, utils.DNSRecord]):
    """
    Applies any relevant document labels
    """
    # for domain in dns_set:
    #     dns = dns_set[domain]
    #     dns.labels = []
    #     # Icinga
    #     if 'icinga' in dns.__dict__:
    #         dns.labels.append('icinga_not_monitored')

@utils.handle
def implied_ptrs(forward_dns: dict[str, utils.DNSRecord], reverse_dns: dict[str, utils.PTRRecord]):
    for ip, ptr in reverse_dns.items():
        ptr.discoverImpliedPTR(forward_dns)


#############
# Main flow #
#############

def main():
    # Run DNS and ext resource plugins
    forward, reverse = {}, {}
    pluginmaster.runStage('dns', forward, reverse)
    pluginmaster.runStage('resource', forward, reverse)

    # apply additional modifications/filters
    ips(forward, reverse)
    flatten(forward)
    apply_roles(forward)
    locations(forward)
    license_keys(forward)
    license_orgs(forward)
    labels(forward)

    # Run remaining plugins
    pluginmaster.runStage('other', forward, reverse)

    utils.writeDNS(forward, 'src/dns.json')
    utils.writeDNS(reverse, 'src/ips.json')
    # Write DNS documents
    utils.xslt('dns.xsl', 'src/dns.xml')
    # Write IP documents
    utils.xslt('ips.xsl', 'src/ips.xml')

    screenshots()
    cleanup.clean()


if __name__ == '__main__':
    init()
    main()
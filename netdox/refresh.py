"""
The main script in Netdox. Manages almost every step of the refresh process from data gathering to writing PSML.

This script is used to provide a central flow for the data refresh.
It runs some initialisation first, then calls the *dns* plugins, the *resource* plugins, does some additional processing,
then calls the final plugin stage and writes PSML. The upload is managed by the caller executable Netdox (see :ref:`file_netdox`)
"""

import license_inf, cleanup, iptools, pageseeder, plugins, utils
import subprocess, shutil, json, os
from distutils.util import strtobool
from bs4 import BeautifulSoup

##################
# Initialisation #
##################

def init():
    """
    Some initialisation to run every time the data is refreshed.

    Removes any leftover output files, initialises all plugins, and loads the dns roles and other config from PageSeeder.
    If this config is not present or Netdox is unable to find or parse it, a default set of config files is copied to the upload context.
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

    # Initialise plugins
    global pluginmaster
    pluginmaster = plugins.pluginmanager()

    # Load user-defined locations
    utils.loadLocations()


    config = {"exclusions": []}
    roles = {}
    # load dns config from pageseeder
    psConfigInf = json.loads(pageseeder.get_uri('_nd_config'))
    if 'title' in psConfigInf and psConfigInf['title'] == 'DNS Config':
        # load a role
        roleFrag = BeautifulSoup(pageseeder.get_fragment('_nd_config', 'roles'), features='xml')
        for xref in roleFrag("xref"):
            roleConfig = pageseeder.pfrag2dict(pageseeder.get_fragment(xref['docid'], 'config'))
            roleName = roleConfig['name']

            # set role for configured domains
            revXrefs = BeautifulSoup(pageseeder.get_xrefs(xref['docid']), features='xml')
            for revXref in revXrefs("reversexref"):
                if 'documenttype' in revXref.attrs and revXref['documenttype'] == 'dns':
                    roles[revXref['urititle']] = roleName
            
            screenshot = strtobool(roleConfig['screenshot'])
            del roleConfig['name'], roleConfig['screenshot']
            
            config[roleName] = (roleConfig | {
                "screenshot": screenshot,
                "domains": []
            })

        # load exclusions
        exclusionSoup = BeautifulSoup(pageseeder.get_fragment('_nd_config', 'exclude'), features='xml')
        for para in exclusionSoup("para"):
            config['exclusions'].append(para.string)

    else:
        print('[WARNING][refresh] No DNS config found on PageSeeder')
        # load default config and copy to upload context
        for file in os.scandir('src/defconf'):
            if file.name != 'config.psml':
                with open(file, 'r') as stream:
                    soup = BeautifulSoup(stream.read(), features='xml')
                    roleConfig = pageseeder.pfrag2dict(soup.find(id="config")) | {'domains':[]}
                    config[roleConfig['name']] = roleConfig

            shutil.copyfile(file.path, f'out/config/{file.name}')


    # load batch defined roles
    tmp = {}
    try:
        with open('src/roles.json', 'r') as stream:
            batchroles = json.load(stream)
    except FileNotFoundError:
        batchroles = {}

    for role, domainset in batchroles.items():
        for domain in domainset:
            tmp[domain] = role
    batchroles = tmp
    # overwrite roles with batchroles where necessary
    roles |= batchroles

    for domain, role in roles.items():
        if role in config:
            config[role]['domains'].append(domain)

    with open('src/config.json', 'w') as stream:
        stream.write(json.dumps(config, indent=2))
    
    utils.loadConfig()


######################
# Critical functions #
######################

def apply_roles(dns_set: utils.DNSSet):
    """
    Applies custom roles defined in the PageSeeder config.

    Deletes any DNS records with names specified in the main config file, and sets the *role* attribute on all other records.
    If a record's name does not appear in the config, it is assigned the *default* role.
    """
    config = utils.config

    for domain in config['exclusions']:
        if domain in dns_set:
            del dns_set[domain]
    
    unassigned = list(dns_set.names)
    for role in config.keys():
        if role != 'exclusions':
            for domain in config[role]['domains']:
                try:
                    dns_set[domain].role = role
                    unassigned.remove(domain)
                except KeyError:
                    pass
    
    for domain in unassigned:
        dns_set[domain].role = 'default'
        config['default']['domains'].append(domain)

def ips(forward: utils.DNSSet, reverse: utils.DNSSet):
    """
    Populates a reverse dns set with any missing IPs from a forward dns set.

    Iterates over every unique and private subnet and generates empty PTR records for any unused IPv4 addresses.
    """
    subnets = set()
    for dns in forward:
        for ip in dns.ips:
            if ip not in reverse:
                reverse.add(utils.PTRRecord(ip))
            if not iptools.public_ip(ip):
                subnets.add(reverse[ip].subnet)
    
    for subnet in subnets:
        for ip in iptools.subn_iter(subnet):
            if ip not in reverse:
                reverse.add(utils.PTRRecord(ip, unused=True))

def screenshots():
    """
    Runs screenshotCompare (see :ref:`file_screenshot`) and writes output using xslt.
    """
    subprocess.run('node screenshotCompare.js', check=True, shell=True)
    utils.xslt('status.xsl', 'src/review.xml', 'out/status_update.psml')


###########################
# Non-essential functions #
###########################

@utils.handle
def locations(dns_set: utils.DNSSet):
    """
    Attempts to extract location data from CNAME records for those DNS records that have none.

    Iterates over the cnames of a record. If any of them have location data, inject into the initial record.
    """
    unlocated = []
    for dns in dns_set:
        if not dns.location:
            for alias in dns.cnames:
                try:
                    if dns_set[alias].location:
                        dns.location = dns_set[alias].location
                except KeyError:
                    pass
        
        if not dns.location:
            unlocated.append(dns.name)
    if unlocated:
        print('[WARNING][refresh] Some records are missing location data. For a complete list see /var/log/unlocated.json')
        with open('/var/log/unlocated.json', 'w') as stream:
            stream.write(json.dumps(unlocated, indent=2))

@utils.handle
def license_keys(dns_set: utils.DNSSet):
    """
    Sets the *license* attribute for any domains with a PageSeeder license.

    Uses the functionality found in :ref:`file_licenses` to add license data to records.
    """
    licenses = license_inf.fetch()
    for domain in licenses:
        if domain in dns_set:
            dns = dns_set[domain]
            dns.license = licenses[domain]
            if dns.role != 'pageseeder':
                print(f'[WARNING][refresh.py] {dns.name} has a PageSeeder license but is using role {dns.role}')

@utils.handle
def license_orgs(dns_set: utils.DNSSet):
    """
    Sets the *org* attribute using the associated PageSeeder license.

    Uses the functionality found in :ref:`file_licenses` to add organisation data to records.
    """
    for record in dns_set:
        if 'license' in record.__dict__:
            org_id = license_inf.org(record.license)
            if org_id:
                record.org = org_id

@utils.handle
def labels(dns_set: utils.DNSSet):
    """
    Applies any relevant document labels

    :meta private:
    """
    # for domain in dns_set:
    #     dns = dns_set[domain]
    #     dns.labels = []
    #     # Icinga
    #     if 'icinga' in dns.__dict__:
    #         dns.labels.append('icinga_not_monitored')

@utils.handle
def implied_ptrs(forward_dns: utils.DNSSet, reverse_dns: utils.DNSSet):
    """
    Calls the ``discoverImpliedPTR`` class method on all PTR records in a reverse dns set.

    For more see :ref:`utils`.
    """
    for ptr in reverse_dns:
        ptr.discoverImpliedPTR(forward_dns)


#############
# Main flow #
#############

def main():
    """
    The main flow of the refresh process.

    Calls most other functions in this script in the required order.
    """
    forward = utils.DNSSet('forward')
    reverse = utils.DNSSet('reverse')

    global pluginmaster
    pluginmaster.runStage('dns', forward, reverse)
    pluginmaster.runStage('resource', forward, reverse)

    # apply additional modifications/filters
    ips(forward, reverse)
    apply_roles(forward)
    if utils.location_map:
        locations(forward)
    license_keys(forward)
    license_orgs(forward)
    labels(forward)

    pluginmaster.runStage('pre-write', forward, reverse)

    # Write DNS sets
    with open('src/forward.json', 'w') as stream:
        stream.write(forward.to_json())
    with open('src/reverse.json', 'w') as stream:
        stream.write(reverse.to_json())
    # Write DNS documents
    utils.xslt('dns.xsl', 'src/forward.xml')
    # Write IP documents
    utils.xslt('ips.xsl', 'src/reverse.xml')

    pluginmaster.runStage('post-write', forward, reverse)

    screenshots()
    cleanup.pre_upload()


if __name__ == '__main__':
    init()
    main()
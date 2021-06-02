"""
The main script in Netdox. Manages almost every step of the refresh process from data gathering to writing PSML.

This script is used to provide a central flow for the data refresh.
It runs some initialisation first, then calls the *dns* plugins, the *resource* plugins, does some additional processing,
then calls the final plugin stage and writes PSML. The upload is managed by the caller executable Netdox (see :ref:`file_netdox`)
"""

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

    #Initialise plugins
    pluginmaster.initPlugins()


    config = {"exclusions": []}
    roles = {}
    # load dns config from pageseeder
    psConfigInf = json.loads(ps_api.get_uri('_nd_config'))
    if psConfigInf['title'] == 'DNS Config':
        # load a role
        roleFrag = BeautifulSoup(ps_api.get_fragment('_nd_config', 'roles'), features='xml')
        for xref in roleFrag("xref"):
            roleConfig = ps_api.pfrag2dict(ps_api.get_fragment(xref['docid'], 'config'))
            roleName = roleConfig['name']

            # set role for configured domains
            revXrefs = BeautifulSoup(ps_api.get_xrefs(xref['docid']), features='xml')
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
        exclusionSoup = BeautifulSoup(ps_api.get_fragment('_nd_config', 'exclude'), features='xml')
        for para in exclusionSoup("para"):
            config['exclusions'].append(para.string)

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
    """
    Takes a set of DNS records and resolves any conflicts caused by capitalisation.

    Modifies the given DNS set in place by combining any DNS records with names that are the same except for captalisation.

    :Args:
        A dictionary of DNS records (see :ref:`utils`)
    """
    for domain in dns_set:
        if (domain.lower() in dns_set) and (dns_set[domain.lower()] is not dns_set[domain]):
            union = utils.merge_sets(dns_set[domain.lower()], dns_set[domain])
            del dns_set[domain]
            dns_set[domain.lower()] = union

@utils.critical
def apply_roles(dns_set: dict[str, utils.DNSRecord]):
    """
    Applies custom roles defined in the PageSeeder config.

    Deletes any DNS records with names specified in the main config file, and sets the *role* attribute on all other records.
    If a record's name does not appear in the config, it is assigned the *default* role.
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
                    unassigned.remove(domain)
                except KeyError:
                    pass
    
    for domain in unassigned:
        try:
            dns_set[domain].role = 'default'
            config['default']['domains'].append(domain)
        except KeyError:
            print('[DEBUG][refresh] Unexpected behaviour: dns_set is missing domain in unassigned')

@utils.critical
def ips(forward: dict[str, utils.DNSRecord], reverse: dict[str, utils.PTRRecord]):
    """
    Populates a reverse dns set with any missing IPs from a forward dns set.

    Iterates over every unique and private subnet and generates empty PTR records for any unused IPv4 addresses.
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
    Runs screenshotCompare (see :ref:`file_screenshot`) and writes output using xslt.
    """
    subprocess.run('node screenshotCompare.js', check=True, shell=True)
    utils.xslt('status.xsl', 'src/review.xml', 'out/status_update.psml')


###########################
# Non-essential functions #
###########################

@utils.handle
def locations(dns_set: dict[str, utils.DNSRecord]):
    """
    Attempts to extract location data from CNAME records for those DNS records that have none.

    Iterates over the cnames of a record. If any of them have location data, inject into the initial record.
    """
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
def license_orgs(dns_set: dict[str, utils.DNSRecord]):
    """
    Sets the *org* attribute using the associated PageSeeder license.

    Uses the functionality found in :ref:`file_licenses` to add organisation data to records.
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

    :meta private:
    """
    # for domain in dns_set:
    #     dns = dns_set[domain]
    #     dns.labels = []
    #     # Icinga
    #     if 'icinga' in dns.__dict__:
    #         dns.labels.append('icinga_not_monitored')

@utils.handle
def implied_ptrs(forward_dns: dict[str, utils.DNSRecord], reverse_dns: dict[str, utils.PTRRecord]):
    """
    Calls the ``discoverImpliedPTR`` class method on all PTR records in a reverse dns set.

    For more see :ref:`utils`.
    """
    for _, ptr in reverse_dns.items():
        ptr.discoverImpliedPTR(forward_dns)


#############
# Main flow #
#############

def main():
    """
    The main flow of the refresh process.

    Calls most other functions in this script in the required order.
    """
    # Run DNS and ext resource plugins
    forward, reverse = {}, {}
    pluginmaster.runStage('dns', forward, reverse)
    pluginmaster.runStage('resource', forward, reverse)

    # apply additional modifications/filters
    ips(forward, reverse)
    flatten(forward)
    apply_roles(forward)
    if utils.location_map:
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
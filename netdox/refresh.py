"""
The main script in Netdox. Manages almost every step of the refresh process from data gathering to writing PSML.

This script is used to provide a central flow for the data refresh.
It runs some initialisation first, then calls the *dns* plugins, the *resource* plugins, does some additional processing,
then calls the final plugin stage and writes PSML. The upload is managed by the caller executable Netdox (see :ref:`file_netdox`)
"""

import json
import os
import shutil
import subprocess
from distutils.util import strtobool

from bs4 import BeautifulSoup

import cleanup
import license_inf
import pageseeder
import plugins
import utils
from networkobjs import Network, Node

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


###########################
# Non-essential functions #
###########################

# @utils.handle
# def license_keys(dns_set: utils.DNSSet):
#     """
#     Sets the *license* attribute for any domains with a PageSeeder license.

#     Uses the functionality found in :ref:`file_licenses` to add license data to records.
#     """
#     licenses = license_inf.fetch()
#     for domain in licenses:
#         if domain in dns_set:
#             dns = dns_set[domain]
#             dns.license = licenses[domain]
#             if dns.role != 'pageseeder':
#                 print(f'[WARNING][refresh.py] {dns.name} has a PageSeeder license but is using role {dns.role}')

# @utils.handle
# def license_orgs(dns_set: utils.DNSSet):
#     """
#     Sets the *org* attribute using the associated PageSeeder license.

#     Uses the functionality found in :ref:`file_licenses` to add organisation data to records.
#     """
#     for record in dns_set:
#         if 'license' in record.__dict__:
#             org_id = license_inf.org(record.license)
#             if org_id:
#                 record.org = org_id


#############
# Main flow #
#############

def main():
    """
    The main flow of the refresh process.

    Calls most other functions in this script in the required order.
    """
    init()
    network = Network(config = utils.config)

    global pluginmaster
    pluginmaster.runStage('dns', network)
    network.ips.fillSubnets()
    network.discoverImpliedLinks()

    # generate generic nodes
    for ip in network.ips.used:
        if ip.is_private:
            network.nodes.add(Node(
                name = ip.addr,
                private_ip = ip.addr, 
                public_ips = [ip.nat] if ip.nat else [],
                domains = ip.domains
            ))

    ## Read hardware docs here

    pluginmaster.runStage('nodes', network)

    network.applyDomainRoles()
    
    pluginmaster.runStage('pre-write', network)
    
    network.dumpNetwork()
    
    # Write Domain documents
    utils.xslt('domains.xsl', 'src/domains.xml')
    # Write IPv4Address documents
    utils.xslt('ips.xsl', 'src/ips.xml')
    # Write Node documents
    utils.xslt('nodes.xsl', 'src/nodes.xml')


    pluginmaster.runStage('post-write', network)

    subprocess.run('node screenshotCompare.js', check=True, shell=True)
    utils.xslt('status.xsl', 'src/review.xml', 'out/status_update.psml')

    cleanup.pre_upload()


if __name__ == '__main__':
    main()

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
    pluginmaster = plugins.PluginManager()
    
    # Add import statements to imports.xslt
    xsltImports = BeautifulSoup(utils.MIN_STYLESHEET, features = 'xml')
    for plugin in pluginmaster.nodes:
        if plugin.xslt:
            importTag = xsltImports.new_tag('import', nsprefix = 'xsl', href = plugin.xslt)
            xsltImports.stylesheet.append(importTag)
    
    with open('imports.xslt', 'w', encoding = 'utf-8') as stream:
        stream.write(xsltImports.prettify())

    roles = {"exclusions": []}
    # load dns config from pageseeder
    psConfigInf = json.loads(pageseeder.get_uri('_nd_config'))
    if 'title' in psConfigInf and psConfigInf['title'] == 'DNS Config':
        # load roles fragment
        roleFrag = BeautifulSoup(pageseeder.get_fragment('_nd_config', 'roles'), features='xml')
        for xref in roleFrag("xref"):
            roleConfig = pageseeder.pfrag2dict(pageseeder.get_fragment(xref['docid'], 'config'))
            roleName = roleConfig['name']

            # set role for configured domains
            domains = set()
            revXrefs = BeautifulSoup(pageseeder.get_xrefs(xref['docid']), features='xml')
            for revXref in revXrefs("reversexref"):
                ## change to 'domain'
                if 'documenttype' in revXref.attrs and revXref['documenttype'] == 'dns':
                    domains.add(revXref['urititle'])
            
            screenshot = strtobool(roleConfig['screenshot'])
            del roleConfig['name'], roleConfig['screenshot']
            
            roles[roleName] = (roleConfig | {
                "screenshot": screenshot,
                "domains": list(domains)
            })

        # load exclusions
        exclusionSoup = BeautifulSoup(pageseeder.get_fragment('_nd_config', 'exclude'), features='xml')
        for para in exclusionSoup("para"):
            roles['exclusions'].append(para.string)

    else:
        print('[WARNING][refresh] No DNS config found on PageSeeder')
        # load default config and copy to upload context
        for file in os.scandir('src/defconf'):
            if file.name != 'config.psml':
                with open(file, 'r') as stream:
                    soup = BeautifulSoup(stream.read(), features='xml')
                    roleConfig = pageseeder.pfrag2dict(soup.find(id="config")) | {'domains':[]}
                    roles[roleConfig['name']] = roleConfig

            shutil.copyfile(file.path, f'out/config/{file.name}')


    # load preconfigured roles
    try:
        with open('src/roles.json', 'r') as stream:
            preconfigured = json.load(stream)
    except FileNotFoundError:
        preconfigured = {}

    # merge preconfigured and ps configured role sets
    for role, roleConfig in preconfigured.items():
        if role == 'exclusions':
            roles[role] = sorted(set(roles[role] + preconfigured[role]))
        else:
            for attribute, value in roleConfig.items():
                if attribute == 'domains':
                    roles[role][attribute] = sorted(set(roles[role][attribute] + value))
                else:
                    roles[role][attribute] = value

    with open('src/roles.json', 'w') as stream:
        stream.write(json.dumps(roles, indent=2))


def main():
    """
    The main flow of the refresh process.

    Calls most other functions in this script in the required order.
    """
    init()
    network = Network(config = utils.config(), roles = utils.roles())

    global pluginmaster
    pluginmaster.initStage('dns')
    pluginmaster.runStage('dns', network)

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

    pluginmaster.initStage('nodes')
    pluginmaster.runStage('nodes', network)

    network.ips.fillSubnets()
    network.domains.applyRoles()
    network.discoverImpliedLinks()
    
    pluginmaster.initStage('pre-write')
    pluginmaster.runStage('pre-write', network)
    
    network.dumpNetwork()
    
    # Write Domain documents
    utils.xslt('domains.xslt', 'src/domains.xml')
    # Write IPv4Address documents
    utils.xslt('ips.xslt', 'src/ips.xml')
    # Write Node documents
    utils.xslt('nodes.xslt', 'src/nodes.xml')


    pluginmaster.initStage('post-write')
    pluginmaster.runStage('post-write', network)

    subprocess.run('node screenshotCompare.js', check=True, shell=True)
    utils.xslt('status.xslt', 'src/review.xml', 'out/status_update.psml')

    cleanup.pre_upload()


if __name__ == '__main__':
    main()

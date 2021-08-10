"""
The main script in Netdox. Manages almost every step of the refresh process from data gathering to writing PSML.

This script is used to provide a central flow for the data refresh.
It runs some initialisation first, then calls the *dns* plugins, the *resource* plugins, does some additional processing,
then calls the final plugin stage and writes PSML. The upload is managed by the caller executable Netdox (see :ref:`file_netdox`)
"""

import json
import os
import shutil
from distutils.util import strtobool

from bs4 import BeautifulSoup

import cleanup
import pageseeder
import psml
import utils
from networkobjs import NetworkManager

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

    roles = {"exclusions": []}
    # load dns config from pageseeder
    psConfigInf = json.loads(pageseeder.get_uri('_nd_config'))
    if 'title' in psConfigInf and psConfigInf['title'] == 'DNS Config':
        # load roles fragment
        roleFrag = BeautifulSoup(pageseeder.get_fragment('_nd_config', 'roles'), features='xml')
        for xref in roleFrag("xref"):
            try:
                roleUri = xref['uriid']
                roleConfig = psml.pfrag2dict(pageseeder.get_fragment(roleUri, 'config'))
                roleName = roleConfig['name']

                # set role for configured domains
                domains = set()
                revXrefs = BeautifulSoup(pageseeder.get_xrefs(roleUri), features='xml')
                for revXref in revXrefs("reversexref"):
                    ## change to 'domain'
                    if 'documenttype' in revXref.attrs and revXref['documenttype'] == 'domain':
                        domains.add(revXref['urititle'])
                
                screenshot = strtobool(roleConfig['screenshot'])
                del roleConfig['name'], roleConfig['screenshot']
                
                roles[roleName] = (roleConfig | {
                    "screenshot": screenshot,
                    "domains": list(domains),
                    "uri": roleUri
                })
            except Exception:
                print(f'[ERROR][refresh] Failed to load DNS role {xref["urititle"]}')

        # load exclusions
        exclusionSoup = BeautifulSoup(pageseeder.get_fragment('_nd_config', 'exclude'), features='xml')
        for para in exclusionSoup("para"):
            roles['exclusions'].append(para.string)

    else:
        print('[WARNING][refresh] No DNS config found on PageSeeder')
        # load default config and copy to upload context
        for file in os.scandir('src/defaults/psconf'):
            if file.name != 'config.psml':
                with open(file, 'r') as stream:
                    soup = BeautifulSoup(stream.read(), features='xml')
                    roleConfig = psml.pfrag2dict(soup.find(id="config")) | {'domains':[]}
                    roles[roleConfig['name']] = roleConfig

            shutil.copyfile(file.path, f'out/config/{file.name}')


    # load preconfigured roles
    preconfigured = utils.roles()

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

    #-------------------------------------------------------------------#
    # Initialisation                                                    #
    #-------------------------------------------------------------------#

    init()
    nwman = NetworkManager()
    nwman.initPlugins()

    #-------------------------------------------------------------------#
    # Primary data-gathering stages                                     #
    #-------------------------------------------------------------------#
    
    nwman.runStage('dns')
    nwman.runStage('nodes')

    #-------------------------------------------------------------------#
    # Generate objects for unused private IPs in used subnets,          #
    # resolve internal links, any pre-write plugins                     #
    #-------------------------------------------------------------------#

    nwman.network.ips.fillSubnets()
    
    nwman.runStage('pre-write')

    #-------------------------------------------------------------------#
    # Write domains, ips, and nodes to json and psml,                   #
    # and run any post-write plugins                                    #
    #-------------------------------------------------------------------#
    
    nwman.network.dumpNetwork()
    nwman.network.writePSML()

    nwman.runStage('post-write')

    #-------------------------------------------------------------------#
    # Clean up, upload, and clean again                                 #
    #-------------------------------------------------------------------#

    cleanup.pre_upload()

    zip = shutil.make_archive('netdox-psml', 'zip', 'out')
    pageseeder.zip_upload(zip, 'website')

    cleanup.post_upload()

    print('[INFO][refresh] Done.')


if __name__ == '__main__':
    main()
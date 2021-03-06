"""
The main script in Netdox. Manages almost every step of the refresh process from data gathering to writing PSML.

This script is used to provide a central flow for the data refresh.
It runs some initialisation first, then calls the plugins, does some additional processing,
and finally writes and uploads PSML to PageSeeder.
"""

import logging
import os
import shutil

from netdox import pageseeder, utils
from netdox import NetworkManager

logger = logging.getLogger(__name__)

##################
# Initialisation #
##################

def init():
    """
    Removes old, populated output directories and recreates them.
    """
    pageseeder.clear_loading_zone()

    if not os.path.exists(utils.APPDIR+ 'out'):
        os.mkdir(utils.APPDIR+ 'out')
    # remove old output files
    for folder in os.scandir(utils.APPDIR+ 'out'):
        if folder.is_dir():
            shutil.rmtree(folder)
        else:
            os.remove(folder)
    
    for outfolder in utils.OUTDIRS:
        os.mkdir(utils.APPDIR+ 'out'+ os.sep+ outfolder)


def main(dry: bool = False):
    """
    The main flow of the refresh process.
    Calls most other functions in this script in the required order.
    """

    if dry: logger.info('Refresh running as dry run: no documents will be uploaded.')

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
    nwman.runStage('nat')
    nwman.runStage('nodes')

    #-------------------------------------------------------------------#
    # Generate objects for unused private IPs in used subnets,          #
    # run any pre-write plugins                                         #
    #-------------------------------------------------------------------#

    nwman.network.ips.fillSubnets()
    nwman.runStage('footers')

    #-------------------------------------------------------------------#
    # Write domains, ips, and nodes to pickle and psml,                 #
    # scan for stale files and generate report,                         #
    # and run any post-write plugins                                    #
    #-------------------------------------------------------------------#

    nwman.network.dump()
    nwman.network.writePSML()
    nwman.runStage('write')
    
    nwman.network.report.addSection(
        utils.stale_report(pageseeder.findStale(utils.OUTDIRS)))
    with open(utils.APPDIR + 'src/warnings.log', 'r') as stream:
        nwman.network.report.logs = stream.read()
    nwman.network.report.writeReport()

    #-------------------------------------------------------------------#
    # Zip, upload, and cleanup                                          #
    #-------------------------------------------------------------------#

    zip = shutil.make_archive(utils.APPDIR+ 'src/netdox-psml', 'zip', utils.APPDIR + 'out')
    if not dry:
        pageseeder.zip_upload(zip, 'website')
    else:
        logger.warning('Did not upload documents due to --dry-run flag.')

    nwman.runStage('cleanup')

    logger.info('Done.')


if __name__ == '__main__':
    main()

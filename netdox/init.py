"""
This script is used to initialise the container for the rest of Netdox.
"""

import os

from bs4 import BeautifulSoup

import utils
from pageseeder import urimap

##################
# Initialisation #
##################

def init():
    """
    Copies any values configured in ``config.json`` into ``pageseeder.properties`` and ``build.xml``,
    creates output directories, and generates some XML to import JSON for core XSLT operations.
    """
    # check that urimap can be generated
    urimap()

    # setting up dirs
    for path in ('out', '/etc/netdox/base'):
        if not os.path.exists(path):
            os.mkdir(path)
            
    for path in ('domains', 'ips', 'nodes', 'screenshots', 'screenshot_history', 'review', 'config'):
        if not os.path.exists('out/'+path):
            os.mkdir('out/'+path)

if __name__ == '__main__':
    init()
"""
This script is used to initialise the container for the rest of Netdox.
"""

import os

from cryptography.fernet import Fernet

##################
# Initialisation #
##################

def init():
    """
    Copies any values configured in ``config.json`` into ``pageseeder.properties`` and ``build.xml``,
    creates output directories, and generates some XML to import JSON for core XSLT operations.
    """

    with open('src/crypto', 'wb') as stream:
        stream.write(Fernet.generate_key())

    # setting up dirs
    for path in ('out', 'logs'):
        if not os.path.exists(path):
            os.mkdir(path)
            
    for path in ('domains', 'ips', 'nodes', 'config'):
        if not os.path.exists('out/'+path):
            os.mkdir('out/'+path)

if __name__ == '__main__':
    init()

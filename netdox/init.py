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
    psauth = utils.config()['pageseeder']

    # check that urimap can be generated
    urimap()

    # setting up dirs
    for path in ('out', '/etc/netdox/base'):
        if not os.path.exists(path):
            os.mkdir(path)
            
    for path in ('domains', 'ips', 'nodes', 'screenshots', 'screenshot_history', 'review', 'config'):
        if not os.path.exists('out/'+path):
            os.mkdir('out/'+path)
    
    # generate xslt json import files
    for type in ('domains', 'ips', 'nodes', 'review'):
        utils.jsonForXslt(f'src/{type}.xml', f'{type}.json')

    # load pageseeder properties and auth info
    with open('src/pageseeder.properties','r') as f: 
        psproperties = f.read()

    # overwrite ps properties with external values
    with open('src/pageseeder.properties','w') as stream:
        for line in psproperties.splitlines():
            property = line.split('=')[0]
            if property in psauth:
                stream.write(f'{property}={psauth[property]}')
            else:
                stream.write(line)
            stream.write('\n')

    # Specify ps group in Ant build.xml
    with open('build.xml','r') as stream: 
        soup = BeautifulSoup(stream, features='xml')
    with open('build.xml','w') as stream:
        soup.find('ps:upload')['group'] = psauth['group']
        stream.write(soup.prettify().split('\n',1)[1]) # remove first line of string as xml declaration


if __name__ == '__main__':
    init()
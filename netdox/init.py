import json, os
from textwrap import dedent
from bs4 import BeautifulSoup
import dnsme_api, utils

##################
# Initialisation #
##################

@utils.critical
def init():
    """
    Initialises container and makes it usable for serve and refresh
    """
    psauth = utils.auth['pageseeder']
    awsauth = utils.auth['aws']

    # generate map of all dns zones
    fetchZones()

    # setting up dirs
    for path in ('out', '/etc/ext/base'):
        if not os.path.exists(path):
            os.mkdir(path)
            
    for path in ('DNS', 'IPs', 'xo', 'aws', 'screenshots', 'screenshot_history', 'review', 'config'):
        if not os.path.exists('out/'+path):
            os.mkdir('out/'+path)
    
    # generate xslt json import files
    for type in ('ips', 'dns', 'vms', 'hosts', 'pools', 'aws', 'review', 'templates'):
        with open(f'src/{type}.xml','w') as stream:
            stream.write(dedent(f"""
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE {type} [
            <!ENTITY json SYSTEM "{type}.json">
            ]>
            <{type}>&json;</{type}>""").strip())

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

    # set up aws iam profile
    with open('src/awsconfig', 'w') as stream:
        stream.write(dedent(f"""
        [default]
        output = json
        region = {awsauth['region']}
        aws_access_key_id = {awsauth['aws_access_key_id']}
        aws_secret_access_key = {awsauth['aws_secret_access_key']}
        """).strip())


def fetchZones():
    zones = {
        "dnsme": {},
        "ad": {},
        "k8s": {},
        "cf": {}
    }    

    for id, domain in dnsme_api.fetchDomains():
        zones['dnsme'][domain] = id
    
    with open('src/zones.json', 'w') as stream:
        stream.write(json.dumps(zones, indent=2))


if __name__ == '__main__':
    init()
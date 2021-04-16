import utils, json, os
from textwrap import dedent
from bs4 import BeautifulSoup

##################
# Initialisation #
##################

@utils.critical
def init():
    """
    Creates dirs and template files, loads authentication data, excluded domains, etc...
    """
    with open('src/authentication.json','r') as authstream:
        auth = json.load(authstream)
        psauth = auth['pageseeder']
        k8sauth = auth['kubernetes']

        kubeconfig(k8sauth)

        for path in ('out', '/etc/ext/base'):
            if not os.path.exists(path):
                os.mkdir(path)
                
        for path in ('DNS', 'IPs', 'k8s', 'xo', 'screenshots', 'screenshot_history', 'review'):
            os.mkdir('out/'+path)
        
        for type in ('ips', 'dns', 'apps', 'workers', 'vms', 'hosts', 'pools', 'review'):
            with open(f'src/{type}.xml','w') as stream:
                stream.write(f"""<?xml version="1.0" encoding="UTF-8"?>
                <!DOCTYPE {type} [
                <!ENTITY json SYSTEM "{type}.json">
                ]>
                <{type}>&json;</{type}>""")

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

        try:
        # Remove manually excluded domains once all dns sources have been queried
            with open('src/exclusions.txt','r') as stream:
                exclusions = stream.read().splitlines()
        except FileNotFoundError:
            print('[INFO][netdox.py] No exclusions.txt detected. All domains will be included.')

    return exclusions


def kubeconfig(auth):
    """
    Generate kubeconfig file
    """
    with open('/opt/app/src/kubeconfig', 'w') as stream:
        clusters = ''
        users = ''
        contexts = ''
        for cluster in auth:
            clusters += f"""
            - cluster:
                server: {auth[cluster]['server']}
              name: {cluster}"""

            users += f"""
            - name: {cluster}
              user:
                token: {auth[cluster]['token']}
            """

            contexts += f"""
            - context:
                cluster: {cluster}
                user: {cluster}
              name: {cluster}
            """

            current = cluster

        stream.write(dedent(f"""
        apiVersion: v1
        Kind: Config
        current-context: {current}
        preferences: {{}}
        clusters: {clusters}
        users: {users}
        contexts: {contexts}
        """))
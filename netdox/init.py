import ps_api, utils, json, os
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
        k8sauth = auth['kubernetes']
        psauth = auth['pageseeder']
        awsauth = auth['aws']

        # generate kubeconfig file
        kubeconfig(k8sauth)

        # setting up dirs
        for path in ('out', '/etc/ext/base'):
            if not os.path.exists(path):
                os.mkdir(path)
                
        for path in ('DNS', 'IPs', 'k8s', 'xo', 'aws', 'screenshots', 'screenshot_history', 'review'):
            os.mkdir('out/'+path)
        
        # generate xslt json import files
        for type in ('ips', 'dns', 'apps', 'workers', 'vms', 'hosts', 'pools', 'aws', 'review'):
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
        with open('/opt/app/src/awsconfig', 'w') as stream:
            stream.write(dedent(f"""
            [default]
            output = json
            region = {awsauth['region']}
            aws_access_key_id = {awsauth['aws_access_key_id']}
            aws_secret_access_key = {awsauth['aws_secret_access_key']}
            """).strip())

        # load exclusions from pageseeder
        exclusions = {'dns': [], 'ss': []}
        exclusions_psml = BeautifulSoup(ps_api.get_fragment('_nd_exclusions','2'), features='xml')
        for line in exclusions_psml("para"):
            no_ss_label = line.find(label='no-screenshot')
            if no_ss_label:
                line = no_ss_label
            else:
                exclusions['dns'].append(line.string.strip())
            exclusions['ss'].append(line.string.strip())
            
        with open('src/exclusions.json', 'w') as output:
            output.write(json.dumps(exclusions, indent=2))


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

if __name__ == '__main__':
    init()
import json
import os
from textwrap import dedent

import boto3
import utils
from networkobjs import IPv4Address, Network, JSONEncoder
from plugins import Plugin as BasePlugin

class Plugin(BasePlugin):
    name = 'aws'
    stage = 'nodes'

    def init(self) -> None:
        if not os.path.exists('plugins/aws/src'):
            os.mkdir('plugins/aws/src')
        os.environ['AWS_CONFIG_FILE'] = f'{os.getcwd()}/plugins/aws/src/awsconfig'

        auth = utils.config()['plugins']['aws']
        # set up aws iam profile
        with open('plugins/aws/src/awsconfig', 'w') as stream:
            stream.write(dedent(f"""
            [default]
            output = json
            region = {auth['region']}
            aws_access_key_id = {auth['aws_access_key_id']}
            aws_secret_access_key = {auth['aws_secret_access_key']}
            """).strip())


        with open(f'plugins/aws/src/aws.xml','w') as stream:
            stream.write(dedent(f"""
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE aws [
            <!ENTITY json SYSTEM "aws.json">
            ]>
            <aws>&json;</aws>""").strip())

    def runner(self, network: Network) -> None:
        """
        Links domains to AWS EC2 instances with the same IP
        """
        client = boto3.client('ec2')
        allEC2 = client.describe_instances()
        for reservation in allEC2['Reservations']:
            for instance in reservation['Instances']:
                # for domain in network.domains:
                #     if instance['PrivateIpAddress'] in dns.ips or instance['PublicIpAddress'] in dns.ips:
                #         dns.link(instance['InstanceId'], 'ec2')
                
                for ip in (instance['PrivateIpAddress'], instance['PublicIpAddress']):
                    if ip not in network.ips:
                        network.add(IPv4Address(ip))

        with open('plugins/aws/src/aws.json', 'w') as stream:
            stream.write(json.dumps(allEC2, indent=2, cls=JSONEncoder))
        utils.xslt('plugins/aws/aws.xsl', 'plugins/aws/src/aws.xml')

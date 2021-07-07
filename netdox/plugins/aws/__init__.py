import json
import os
from textwrap import dedent
from typing import Iterable

import boto3
import utils
from networkobjs import IPv4Address, Node, Network, JSONEncoder
from plugins import Plugin as BasePlugin

class EC2Instance(Node):
    def __init__(self, 
            name: str,
            id: str,
            mac: str,
            type: str,
            monitoring: str,
            region: str, 
            tags: Iterable[dict],
            private_ip: str,
            public_ips: Iterable[str] = None,
            domains: Iterable[str] = None
        ) -> None:
        super().__init__(name, private_ip, public_ips, domains, 'AWS EC2 Instance')
        self.id = id.strip().lower()
        self.mac = mac.strip().lower()
        self.instance_type = type
        self.monitoring = monitoring
        self.region = region

        self.tags = {}
        for tag in tags:
            self.tags[tag['Key']] = tag['Value']


class Plugin(BasePlugin):
    name = 'aws'
    stages = ['nodes']
    xslt = 'plugins/aws/nodes.xslt'

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


    def runner(self, network: Network, *_) -> None:
        """
        Links domains to AWS EC2 instances with the same IP
        """
        client = boto3.client('ec2')
        allEC2 = client.describe_instances()
        for reservation in allEC2['Reservations']:
            for instance in reservation['Instances']:
                netInf = instance['NetworkInterfaces'][0]

                network.add(EC2Instance(
                    name = instance['KeyName'],
                    id = instance['InstanceID'],
                    mac = netInf['MacAddress'],
                    monitoring = instance['Monitoring']['State'],
                    region = instance['Placement']['AvailabilityZone'],
                    tags = instance['Tags'],
                    private_ip = netInf['PrivateIpAddress'],
                    public_ips = [netInf['Association']['PublicIp']],
                    domains = [netInf['Association']['PublicDnsName']]
                ))
                
                for ip in (instance['PrivateIpAddress'], instance['PublicIpAddress']):
                    if ip not in network.ips:
                        network.add(IPv4Address(ip))
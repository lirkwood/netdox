import os
from textwrap import dedent
from typing import Iterable

import boto3
from bs4.element import Tag

from netdox import psml, utils
from netdox.networkobjs import DefaultNode, IPv4Address, Network
from netdox.plugins import BasePlugin as BasePlugin


class EC2Instance(DefaultNode):
    """A single instance running on AWS EC2."""
    id: str
    """Instance ID."""
    mac: str
    """MAC address of this instance."""
    instance_type: str
    """Type of EC2 instance."""
    monitoring: str
    """The status of this instance's monitoring."""
    region: str
    """The region this instance belongs to."""
    tags: dict[str, str]
    """Dictionary of tags applied to this instance."""
    type: str = 'AWS EC2 Instance'

    def __init__(self, 
            network: Network,
            name: str,
            id: str,
            mac: str,
            instance_type: str,
            monitoring: str,
            region: str, 
            tags: Iterable[dict],
            private_ip: str,
            public_ips: Iterable[str] = None,
            domains: Iterable[str] = None
        ) -> None:
        super().__init__(network, name, private_ip, public_ips, domains)

        self.id = id.strip().lower()
        self.mac = mac.strip().lower()
        self.instance_type = instance_type
        self.monitoring = monitoring
        self.region = region

        self.tags = {}
        for tag in tags:
            if tag['Value']:
                self.tags[tag['Key']] = tag['Value']

    @property
    def psmlInstanceinf(self) -> Tag:
        """
        Instanceinf fragment of EC2Instance Node document.

        :return: A *properties-fragment* bs4 tag.
        :rtype: Tag
        """
        frag = Tag(is_xml = True, name = 'properties-fragment', attrs = {'id':'instanceinf'})
        frag.append(psml.newprop(
            name='instanceId', title='Instance ID', value=self.id
        ))
        frag.append(psml.newprop(
            name='mac', title='MAC Address', value=self.mac
        ))
        frag.append(psml.newprop(
            name='instanceType', title='Instance Type', value=self.instance_type
        ))
        frag.append(psml.newprop(
            name='Monitoring', title='Monitoring', value=self.monitoring
        ))
        frag.append(psml.newprop(
            name='availabilityZone', title='Availability Zone', value=self.region
        ))
        return frag

    @property
    def psmlTags(self) -> Tag:
        """
        Tags fragment of EC2Instance Node document.

        :return: A *properties-fragment* bs4 tag.
        :rtype: Tag
        """
        frag = Tag(is_xml = True, name = 'properties-fragment', attrs = {'id':'tags'})
        for tag, value in self.tags.items():
            frag.append(psml.newprop(
                name='tag', title=tag, value=value
            ))
        return frag

    @property
    def psmlBody(self) -> Iterable[Tag]:
        section = Tag(is_xml=True, name='section', attrs={'id':'body'})
        section.append(self.psmlInstanceinf)
        section.append(self.psmlTags)
        return [section]

class Plugin(BasePlugin):
    name = 'aws'
    stages = ['nodes']

    def init(self) -> None:
        if not os.path.exists(utils.APPDIR+ 'plugins/aws/src'):
            os.mkdir(utils.APPDIR+ 'plugins/aws/src')
        os.environ['AWS_CONFIG_FILE'] = utils.APPDIR+ 'plugins/aws/src/awsconfig'

        auth = utils.config()['plugins']['aws']
        # set up aws iam profile
        with open(utils.APPDIR+ 'plugins/aws/src/awsconfig', 'w') as stream:
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
                if instance['NetworkInterfaces']:
                    netInf = instance['NetworkInterfaces'][0]
                else:
                    print(f'[WARNING][aws] Instance {instance["InstanceId"]} has no network interfaces and has been ignored')
                    continue

                EC2Instance(
                    network = network,
                    name = instance['KeyName'],
                    id = instance['InstanceId'],
                    mac = netInf['MacAddress'],
                    instance_type = instance['InstanceType'],
                    monitoring = instance['Monitoring']['State'],
                    region = instance['Placement']['AvailabilityZone'],
                    tags = instance['Tags'],
                    private_ip = netInf['PrivateIpAddress'],
                    public_ips = [netInf['Association']['PublicIp']],
                    domains = [netInf['Association']['PublicDnsName']]
                )
                
                for ip in (instance['PrivateIpAddress'], instance['PublicIpAddress']):
                    if ip not in network.ips:
                        IPv4Address(network, ip)

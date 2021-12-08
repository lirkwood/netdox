import json
import logging
import os
from textwrap import dedent
from typing import Iterable

import boto3
from bs4.element import Tag
from netdox import DefaultNode, IPv4Address, Network, psml, utils

logger = logging.getLogger(__name__)
logging.getLogger('botocore').setLevel(logging.WARNING)

## node subclass

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
    type: str = 'ec2'

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
        super().__init__(
            network, 
            name, 
            private_ip, 
            public_ips if public_ips else [], 
            domains if domains else []
        )

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
        frag.append(psml.Property(
            name='instanceId', title='Instance ID', value=self.id
        ))
        frag.append(psml.Property(
            name='mac', title='MAC Address', value=self.mac
        ))
        frag.append(psml.Property(
            name='instanceType', title='Instance Type', value=self.instance_type
        ))
        frag.append(psml.Property(
            name='Monitoring', title='Monitoring', value=self.monitoring
        ))
        frag.append(psml.Property(
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
            frag.append(psml.Property(
                name='tag', title=tag, value=value
            ))
        return frag

    @property
    def psmlBody(self) -> list[Tag]:
        section = Tag(is_xml=True, name='section', attrs={'id':'body'})
        section.append(self.psmlInstanceinf)
        section.append(self.psmlTags)
        return [section]

## plugin funcs

def init() -> None:
    if not os.path.exists(utils.APPDIR+ 'plugins/aws/src'):
        os.mkdir(utils.APPDIR+ 'plugins/aws/src')
    os.environ['AWS_CONFIG_FILE'] = utils.APPDIR+ 'plugins/aws/src/awsconfig'

    auth = utils.config('aws')
    # set up aws iam profile
    with open(utils.APPDIR+ 'plugins/aws/src/awsconfig', 'w') as stream:
        stream.write(dedent(f"""
        [default]
        output = json
        region = {auth['region']}
        aws_access_key_id = {auth['aws_access_key_id']}
        aws_secret_access_key = {auth['aws_secret_access_key']}
        """).strip())


def runner(network: Network) -> None:
    """
    Links domains to AWS EC2 instances with the same IP
    """
    client = boto3.client('ec2')
    allEC2 = client.describe_instances()
    for reservation in allEC2['Reservations']:
        for instance in reservation['Instances']:
            if instance['NetworkInterfaces']:
                netInf = instance['NetworkInterfaces'][0]
                if 'Association' in netInf:
                    dns = {
                        'public_ips': [netInf['Association']['PublicIp']],
                        'domains': [netInf['Association']['PublicDnsName']]
                    }
                else:
                    dns = {'public_ips': [], 'domains': []}
            else:
                logger.warning(f'Instance {instance["InstanceId"]} has no network interfaces and has been ignored')
                continue

            try:
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
                    **dns
                )
            except KeyError:
                logger.error('AWS Key error: \n'+ str(netInf))

## metadata

__stages__ = {'nodes': runner}
__nodes__ = [EC2Instance]
__config__ = {
    'region': str,
    'aws_access_key_id': str,
    'aws_secret_access_key': str
}

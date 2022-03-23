import logging
import os
from datetime import date, datetime, time, timedelta
from textwrap import dedent

import boto3
from netdox import Network, utils
from netdox.plugins.aws.objs import (AWSBillingGranularity, AWSBillingMetrics, AWSTimePeriod,
                                     EC2Instance)

logger = logging.getLogger(__name__)
logging.getLogger('botocore').setLevel(logging.WARNING)

EC2_SERVICE_NAME = 'Amazon Elastic Compute Cloud - Compute'
"""Name of the EC2 service to use in boto3 filters."""

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
    granularity = AWSBillingGranularity.DAILY
    allBilling = _get_billing(granularity)
    allEC2 = boto3.client('ec2').describe_instances()

    for reservation in allEC2['Reservations']:
        for instance in reservation['Instances']:
            if instance['NetworkInterfaces']:
                netInf = instance['NetworkInterfaces'][0]
                dns = {
                    'public_ips': [netInf['Association']['PublicIp']],
                    'domains': [netInf['Association']['PublicDnsName']]
                } if 'Association' in netInf else {
                    'public_ips': [], 'domains': []
                }

                try:
                    id = instance['InstanceId']
                    instance_billing = allBilling[id] if id in allBilling else AWSBillingMetrics(
                        id = id, period = granularity.period(),
                        AmortizedCost = None, UnblendedCost = None, UsageQuantity = None
                    )
                    if id not in allBilling:
                        logger.warning('No billing data for instance: ' + id)
                    EC2Instance(
                        network = network,
                        id = id,
                        mac = netInf['MacAddress'],
                        instance_type = instance['InstanceType'],
                        monitoring = instance['Monitoring']['State'],
                        region = instance['Placement']['AvailabilityZone'],
                        key_pair = instance['KeyName'],
                        state = instance['State']['Name'],
                        billing = instance_billing,
                        tags = instance['Tags'],
                        private_ip = netInf['PrivateIpAddress'],
                        **dns
                    )
                except KeyError:
                    logger.error('AWS Key error: \n'+ str(netInf))
            else:
                logger.warning(f'Instance {instance["InstanceId"]} has no network interfaces and has been ignored')

def _get_billing(granularity: AWSBillingGranularity) -> dict[str, AWSBillingMetrics]:
    """
    Retrieves billing data grouped by resource ID.

    :param start: Start date for the billing period.
    :type start: date
    :param granularity: Granularity of the billing period.
    :type granularity: EC2BillingGranularity
    :return: A dict mapping resource ID to a billing object. 
    :rtype: dict[str, EC2BillingMetrics]
    """
    logger.debug('Fetching billing data.')
    logger.debug(f'Granularity: {granularity.name}')
    logger.debug(f'Period: {granularity.period()}')

    billing = boto3.client('ce').get_cost_and_usage_with_resources(
        TimePeriod = granularity.period().to_dict(),
        Granularity = granularity.name,
        Filter = {'Dimensions': {'Key': 'SERVICE', 'Values': [EC2_SERVICE_NAME]}},
        Metrics = AWSBillingMetrics.METRICS,
        GroupBy = [{
            'Type': 'DIMENSION',
            'Key': 'RESOURCE_ID'
        }]
    )

    metrics = {}
    period = AWSTimePeriod.from_dict(billing['ResultsByTime'][-1]['TimePeriod'])
    logger.debug('Received billing data.')
    for resource in billing['ResultsByTime'][-1]['Groups']:
        id = resource['Keys'][0]
        metrics[id] = AWSBillingMetrics(
            id = id,
            period = period,
            AmortizedCost = float(resource['Metrics']['AmortizedCost']['Amount']),
            UnblendedCost = float(resource['Metrics']['UnblendedCost']['Amount']),
            UsageQuantity = float(resource['Metrics']['UsageQuantity']['Amount'])
        )
    return metrics

## metadata

__stages__ = {'nodes': runner}
__nodes__ = [EC2Instance]
__config__ = {
    'region': '',
    'aws_access_key_id': '',
    'aws_secret_access_key': ''
}

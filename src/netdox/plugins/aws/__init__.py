import logging
import os
from collections import defaultdict
from shutil import rmtree
from textwrap import dedent

import boto3
from netdox import Network, utils
from netdox.app import LifecycleStage
from netdox.plugins.aws.objs import (FORTNIGHT, AWSBillingGranularity,
                                     AWSBillingMetrics, AWSBillingReport,
                                     AWSTimePeriod, EBSSnapshot, EBSVolume,
                                     EBSVolumeState, EC2Instance, SecurityGroup)

logger = logging.getLogger(__name__)
logging.getLogger('botocore').setLevel(logging.WARNING)

EC2_INSTANCE_SERVICE_NAME = 'Amazon Elastic Compute Cloud - Compute'
"""Name of the EC2 instance service."""
EBS_OUTPUT_DIR = os.path.join(utils.APPDIR, 'out', 'aws_ebs')
"""Directory to write EBSVolume documents to."""
SECURITY_GROUP_OUTPUT_DIR = os.path.join(utils.APPDIR, 'out', 'aws_secgroup')
"""Directory to write SecurityGroup documents to."""

def init(_: Network) -> None:
    if not os.path.exists(utils.APPDIR+ 'plugins/aws/src'):
        os.mkdir(utils.APPDIR+ 'plugins/aws/src')
    os.environ['AWS_CONFIG_FILE'] = utils.APPDIR+ 'plugins/aws/src/awsconfig'

    if os.path.exists(EBS_OUTPUT_DIR):
        rmtree(EBS_OUTPUT_DIR)
    os.mkdir(EBS_OUTPUT_DIR)

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
    snapshots = _get_snapshots()
    volumes = _get_volumes(snapshots)

    _create_instances(network, _get_billing(AWSBillingGranularity.MONTHLY), volumes)


# TODO find alternative to global var
global all_volumes
all_volumes: set[EBSVolume] = set()

def write(_: Network) -> None:
    global all_volumes
    for volume in all_volumes:
        with open(
            f'{EBS_OUTPUT_DIR}/{volume.docid}.psml', 
            mode = 'w', encoding = 'utf-8'
        ) as stream:
            stream.write(volume.to_psml())

    for group in _get_security_groups():
        with open(f'{SECURITY_GROUP_OUTPUT_DIR}/{group.docid}.psml', mode = 'w', encoding = 'utf-8') as stream:
            stream.write(group.to_psml())

def _get_security_groups() -> list[SecurityGroup]:
    groups = []
    for item in boto3.client('ec2').describe_security_groups():
        groups.append(SecurityGroup.from_resp(item))
    return groups


def _get_billing(granularity: AWSBillingGranularity) -> AWSBillingReport:
    """
    Retrieves billing data grouped by resource ID.

    :param granularity: Granularity of the billing period.
    :type granularity: EC2BillingGranularity
    :return: A dict mapping resource ID to a billing object. 
    :rtype: dict[str, EC2BillingMetrics]
    """
    logger.debug('Fetching billing data.')
    logger.debug(f'Granularity: {granularity.name}')

    period = (min(granularity.period(), FORTNIGHT))
    logger.debug(f'Period: {period}')

    billing = boto3.client('ce').get_cost_and_usage_with_resources(
        TimePeriod = period.to_dict(),
        Granularity = 'MONTHLY',
        Filter = {'Dimensions': {
            'Key': 'SERVICE', 'Values': [EC2_INSTANCE_SERVICE_NAME]
        }},
        Metrics = AWSBillingMetrics.METRICS,
        GroupBy = [{
            'Type': 'DIMENSION',
            'Key': 'RESOURCE_ID'
        }]
    )

    report = AWSBillingReport(granularity)
    period = AWSTimePeriod.from_dict(billing['ResultsByTime'][-1]['TimePeriod'])
    logger.debug('Received billing data.')

    result = None
    result_period = None
    for _result in billing['ResultsByTime']:
        _result_period = AWSTimePeriod.from_dict(_result['TimePeriod'])
        if result is None or _result_period > result_period:
            result = _result
            result_period = _result_period

    if not (result and result_period):
        raise ValueError("Failed to parse billing from response.")

    for resource in result['Groups']: # type: ignore #TODO get boto3 typing
        report.add_metrics(resource['Keys'][0], AWSBillingMetrics(
            period = result_period,
            AmortizedCost = float(resource['Metrics']['AmortizedCost']['Amount']),
            UnblendedCost = float(resource['Metrics']['UnblendedCost']['Amount']),
            UsageQuantity = float(resource['Metrics']['UsageQuantity']['Amount'])
        ))
    return report

def _get_snapshots() -> defaultdict[str, list[EBSSnapshot]]:
    """
    Retrieves EBSSnapshots mapped to their EBSVolume IDs.

    :return: A dict mapping volume IDs to their snapshots.
    :rtype: dict[str, list[EBSSnapshot]]
    """
    logger.debug("Fetching snapshots.")

    volume_snapshots: defaultdict[str, list[EBSSnapshot]] = defaultdict(list)
    for snapshot in boto3.client('ec2').describe_snapshots()['Snapshots']:
        volume_id = snapshot['VolumeId']
        volume_snapshots[volume_id].append(EBSSnapshot(
            id = snapshot['SnapshotId'],
            size = snapshot['VolumeSize'],
            volume_id = volume_id,
            started = snapshot['StartTime'],
            description = snapshot['Description']
        ))
    return volume_snapshots

#TODO find alternative to nested dict
def _get_volumes(snapshots: dict[str, list[EBSSnapshot]]) -> defaultdict[str, dict[str, EBSVolume]]:
    """
    Retrieves EBSVolumes mapped to their EC2Instance IDs.

    :return: A dict mapping instance ID to a map of attached volumes.
    :rtype: dict[str, list[EBSVolume]]
    """
    logger.debug("Fetching volumes.")

    global all_volumes
    instance_volumes: defaultdict[str, dict[str, EBSVolume]] = defaultdict(dict)
    for volume in boto3.client('ec2').describe_volumes()['Volumes']:
        volume_id = volume['VolumeId']
        parsed_volume = EBSVolume(
            id = volume_id,
            size = volume['Size'],
            type = volume['VolumeType'],
            created = volume['CreateTime'],
            state = EBSVolumeState(volume['State']),
            instance_ids = frozenset({
                att['InstanceId'] for att in volume['Attachments']
            }),
            multi_attach = volume['MultiAttachEnabled'],
            snapshots = frozenset(snapshots[volume_id])
        )

        for attachment in volume['Attachments']:
            instance_id, mount_path = attachment['InstanceId'], attachment['Device']
            instance_volumes[instance_id][mount_path] = parsed_volume
        all_volumes.add(parsed_volume)

    return instance_volumes

def _create_instances(
        network: Network,
        billing: AWSBillingReport, 
        volumes: defaultdict[str, dict[str, EBSVolume]]
    ) -> None:
    """
    Instantiates NetworkObjects for EC2 instances.

    :param billing: Dict mapping EC2 instance ID to some billing metrics.
    :type billing: dict[str, AWSBillingMetrics]
    :param volumes: Dict mapping EC2 instance ID to another dict, 
    mapping mount path to attached volume.
    :type volumes: defaultdict[str, dict[str, EBSVolume]]
    """
    allEC2 = boto3.client('ec2').describe_instances()
    for reservation in allEC2['Reservations']:
        for instance in reservation['Instances']:
            if instance['NetworkInterfaces']:
                netInf = instance['NetworkInterfaces'][0]
                dns = {
                    'public_ips': [netInf['Association']['PublicIp']],
                    'domains': [netInf['Association']['PublicDnsName']]
                } if 'Association' in netInf else {'public_ips': [], 'domains': []}
                secGroups = [ group['GroupId'] for group in instance["GroupSet"] ]

                try:
                    id = instance['InstanceId']
                    EC2Instance(
                        network = network,
                        id = id,
                        mac = netInf['MacAddress'],
                        instance_type = instance['InstanceType'],
                        monitoring = instance['Monitoring']['State'],
                        region = instance['Placement']['AvailabilityZone'],
                        key_pair = instance['KeyName'],
                        state = instance['State']['Name'],
                        billing = billing.get_metrics(id),
                        volumes = volumes[id],
                        security = secGroups,
                        tags = instance['Tags'],
                        private_ip = netInf['PrivateIpAddress'],
                        **dns
                    )
                except KeyError:
                    logger.error('AWS Key error: \n'+ str(netInf))
            else:
                logger.warning(f'Instance {instance["InstanceId"]} has no network interfaces and has been ignored')

## metadata

__stages__ = {
    LifecycleStage.INIT: init,
    LifecycleStage.NODES: runner,
    LifecycleStage.WRITE: write
}
__nodes__ = [EC2Instance]
__config__ = {
    'region': '',
    'aws_access_key_id': '',
    'aws_secret_access_key': ''
}
__output__ = {'aws_ebs', 'aws_secgroup'}

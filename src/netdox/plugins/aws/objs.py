from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import Enum
from functools import cache
from math import ceil
from typing import Iterable, Optional
import re

from bs4 import BeautifulSoup

from netdox import DefaultNode, Network, psml, utils
from netdox.plugins.aws.templates import EBS_VOLUME_TEMPLATE


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
    key_pair: str
    """Name of the key pair that can be used to access this instance."""
    state: str
    """State of the instance at the time of the refresh."""
    billing: AWSBillingMetrics
    """Billing metrics associated with this instance for the current day."""
    volumes: dict[str, EBSVolume]
    """Mount points of volumes mapped to volume objects."""
    tags: dict[str, str]
    """Dictionary of tags applied to this instance."""
    NAME_TAG_KEY: str = 'Name'
    """Tag key that should be mapped to instance name."""
    type: str = 'ec2'

    def __init__(self, 
            network: Network,
            id: str,
            mac: str,
            instance_type: str,
            monitoring: str,
            region: str,
            key_pair: str,
            state: str,
            billing: AWSBillingMetrics,
            volumes: dict[str, EBSVolume],
            tags: Iterable[dict],
            private_ip: str,
            public_ips: Iterable[str] = None,
            domains: Iterable[str] = None
        ) -> None:

        self.tags = {}
        for tag in tags:
            if tag['Value']:
                self.tags[tag['Key']] = tag['Value']

        super().__init__(
            network, 
            self.tags[self.NAME_TAG_KEY], 
            private_ip, 
            public_ips if public_ips else [], 
            domains if domains else []
        )

        self.id = id.strip().lower()
        self.mac = mac.strip().lower()
        self.instance_type = instance_type
        self.monitoring = monitoring
        self.region = region
        self.key_pair = key_pair
        self.state = state
        self.billing = billing
        self.volumes = volumes

    @property
    def psmlGeneral(self) -> psml.PropertiesFragment:
        """
        General info fragment of EC2Instance Node document.

        :return: A *properties-fragment* bs4 tag.
        :rtype: Tag
        """
        return psml.PropertiesFragment('general', [
            psml.Property('instanceId', self.id, 'Instance ID'),
            psml.Property('mac', self.mac, 'MAC Address'),
            psml.Property('instanceType', self.instance_type, 'Instance Type'),
            psml.Property('monitoring', self.monitoring, 'Monitoring'),
            psml.Property('availabilityZone', self.region, 'Availability Zone'),
            psml.Property('key_pair', self.key_pair, 'Key Pair'),
            psml.Property('state', self.state, 'State')
        ])

    @property
    def psmlTags(self) -> psml.PropertiesFragment:
        """
        Tags fragment of EC2Instance Node document.

        :return: A *properties-fragment* bs4 tag.
        :rtype: Tag
        """
        return psml.PropertiesFragment('tags', [
            psml.Property('tag', value, f'Tag: {tag}')
            for tag, value in self.tags.items()
        ])

    @property
    def psmlVolumes(self) -> list[psml.PropertiesFragment]:
        return  [
            psml.PropertiesFragment(f'volume_{count}', [
                psml.Property(
                    'volume', 
                    psml.XRef(docid = volume.docid), 
                    'Attached Volume'
                ),
                psml.Property('mount_path', path, 'Mount Path'),
                # TODO replace this property with cumulative volume cost in billing frag
                psml.Property(
                    'amortized_cost', 
                    str(volume.get_billing(self.billing.period).AmortizedCost or 0), 
                    'Amortized Cost'
                )
            ]) for count, (path, volume) in enumerate(self.volumes.items())
        ]

    @property
    def psmlBody(self) -> list[psml.Section]:
        return [
            psml.Section('body', fragments = [
                self.psmlGeneral, 
                self.psmlTags,
                self.billing.to_psml(),
            ] + self.psmlVolumes)
        ]

## Volumes

@cache
def _get_volume_pricing() -> dict[str, float]:
    """
    Gets the pricing data for EBSVolumes.

    :return: A dict mapping EBSVolume type to price in USD/GB/Hour
    :rtype: dict[str, int]
    """
    #TODO implement
    return {'gp2': 0.12, 'gp3': 0.096}

class EBSVolumeState(Enum):
    CREATING = 'creating'
    AVAILABLE = 'available'
    IN_USE = 'in-use'
    DELETING = 'deleting'
    DELETED = 'deleted'
    ERROR = 'error'

@dataclass(frozen = True)
class EBSVolume:
    """A single AWS EBS volume."""
    id: str
    """Volume ID."""
    size: int
    """Volume size in GiB."""
    type: str
    """The EBS volume type."""
    created: datetime
    """The date and time this volume was created."""
    state: EBSVolumeState
    """Current state of this volume."""
    instance_ids: frozenset[str]
    """IDs of instances this volume is attached to."""
    multi_attach: bool
    """Whether this volume can be attached to multiple instances at once."""
    snapshots: frozenset[EBSSnapshot]
    """List of snapshots of this volume."""

    NONEXISTENT_ID = 'vol-ffffffff'
    """ID of a volume that no longer exists."""
    _GiB_TO_GB = 1024**3 / 1000**3
    """Constant to multiply size in GiB by to acquire size in GB."""

    @property
    def docid(self) -> str:
        """
        The docid of this objects PSML document.

        :return: A string valid as a PageSeeder docid.
        :rtype: str
        """
        return f'_nd_aws_volume_{re.sub(utils.docid_invalid_pattern, "_", self.id)}'

    @cache
    def get_billing(self, period: AWSTimePeriod) -> AWSBillingMetrics:
        """
        Calculates the billing metrics for this object over the given period.

        :param period: _description_
        :type period: AWSTimePeriod
        :raises AttributeError: _description_
        :return: _description_
        :rtype: AWSBillingMetrics
        """
        #TODO check if created after period begins
        # start = max(self.created., period.start)
        start = period.start
        hours = ceil((period.end - start).total_seconds() / 3600)
        size_gb = self.size * self._GiB_TO_GB
        gb_months = size_gb * hours / 730
        
        try:
            cost = gb_months * _get_volume_pricing()[self.type]
        except KeyError:
            raise AttributeError(
                f'Failed to retrieve pricing data for EBSVolume of type: {self.type}')
        return AWSBillingMetrics(self.id, period, cost, cost, gb_months)

    def to_psml(self) -> str:
        """
        Returns the PSML document representing this object.

        :return: This document as a PSML document from the template.
        :rtype: str
        """
        #TODO move this into common code
        doc = str(EBS_VOLUME_TEMPLATE)
        for field in re.findall(r'(#![a-zA-Z0-9_]+)', EBS_VOLUME_TEMPLATE):
            attr = getattr(self, field.replace('#!',''), None)
            #TODO add empty string validation
            if attr is not None:
                if not isinstance(attr, str):
                    try:
                        attr = str(attr)
                    except Exception:
                        continue
                doc = re.sub(field, attr, doc)
            else:
                doc = re.sub(field, '—', doc)
        
        soup = BeautifulSoup(doc, 'xml')
        details_section = soup.find('section', id = 'details')
        for count, snapshot in enumerate(self.snapshots):
            details_section.append(psml.PropertiesFragment(f'snapshot_{count}', [
                psml.Property('snapshotId', snapshot.id, 'Snapshot ID'),
                psml.Property('started', str(snapshot.started), 'Start Time'),
                psml.Property('description', snapshot.description, 'Description')
            ]).tag)

        return str(soup)

@dataclass(frozen = True)
class EBSSnapshot:
    """A snapshot backup of an EBSVolume."""
    id: str
    """Snapshot ID."""
    size: int
    """Volume size in GiB."""
    volume_id: str
    """ID of the volume this is a snapshot of."""
    started: datetime
    """The date and time this snapshot was started."""
    description: str
    """Description of this snapshot."""

## Billing

@dataclass(frozen = True)
class AWSTimePeriod:
    """Object for parsing/serialising to TimePeriod format used in boto3."""
    start: datetime
    """Start of the time period — inclusive."""
    end: datetime
    """End of the time period — exclusive."""
    _start_key: str = 'Start'
    _end_key: str = 'End'

    def __str__(self) -> str:
        start = self.start.isoformat(timespec = 'seconds')
        end = self.end.isoformat(timespec = 'seconds')
        return f'From {start} to {end}'

    def to_dict(self) -> dict[str, str]:
        """
        Returns a dictionary representing this object, usable in boto3 calls.
        """
        return {
            # self._start_key: self.start.strftime('%Y-%m-%dT%H:%M:%SZ'),
            # self._end_key: self.end.strftime('%Y-%m-%dT%H:%M:%SZ')
            self._start_key: self.start.strftime('%Y-%m-%d'),
            self._end_key: self.end.strftime('%Y-%m-%d')
        }

    @classmethod
    def from_dict(cls, period: dict[str, str]) -> AWSTimePeriod:
        """
        Instantiates a AWSTimePeriod from a time period dictionary returned by boto3.

        :param period: A dictionary like that returned by *to_dict()*.
        :type period: dict[str, str]
        :return: An AWSTimePeriod object.
        :rtype: AWSTimePeriod
        """
        return cls(
            start = datetime.fromisoformat(period[cls._start_key].strip('Z')),
            end = datetime.fromisoformat(period[cls._end_key].strip('Z'))
        )
    
class AWSBillingGranularity(Enum):
    """Represents the granularity of an AWS billing report.
    Values of members are the length of a period of the given granularity."""
    HOURLY = timedelta(hours = 1)
    DAILY = timedelta(days = 1)
    MONTHLY = timedelta(weeks = 4)

    @cache
    def period(self) -> AWSTimePeriod:
        """
        Returns a AWSTimePeriod object ending at midnight on the current day.
        Start time is twice the value of the granularity before the end time.
        e.g. For DAILY the period will start 2 days before midnight, current day.

        :return: A dict mapping Start/End to a time in AWS-compliant format.
        :rtype: dict[str, str]
        """
        today = datetime.combine(date.today(), time())
        return AWSTimePeriod(today - (2 * self.value), today)

@dataclass(frozen = True)
class AWSBillingMetrics:
    """Stores the billing metrics for an AWS resource."""
    id: str
    """Resource ID these metrics are associated with."""
    period: AWSTimePeriod
    """The time period over which the metrics were measured."""
    AmortizedCost: Optional[float]
    """Unblended cost combined with amortized reservation cost."""
    UnblendedCost: Optional[float]
    """Usage costs charged during the relevant period."""
    UsageQuantity: Optional[float]
    """Amount the associated resource was used during the relevant period."""
    METRICS: tuple[str, str, str] = (
        'AmortizedCost', 
        'UnblendedCost',
        'UsageQuantity'
    )
    """The names of the billing metrics this class stores."""

    def to_psml(self) -> psml.PropertiesFragment:
        amortized = str(round(self.AmortizedCost, 2)) if self.AmortizedCost else 'None'
        unblended = str(round(self.UnblendedCost, 2)) if self.UnblendedCost else 'None'
        usage = str(round(self.UsageQuantity, 2)) if self.UsageQuantity else 'None'

        return psml.PropertiesFragment('billing', [
            psml.Property('period', str(self.period), 'Billing Period'),
            psml.Property('amortized_cost', amortized, 'Amortized Cost (USD)'),
            psml.Property('unblended_cost', unblended, 'Unblended Cost (USD)'),
            psml.Property('usage', usage, 'Usage Quantity')
        ])

class AWSBillingReport:
    granularity: AWSBillingGranularity
    """Granularity of the billing report."""
    _metrics: dict[str, AWSBillingMetrics]
    """Dict mapping resource ID to associated billing metrics."""

    def __init__(self, 
        granularity: AWSBillingGranularity, 
        metrics: dict[str, AWSBillingMetrics] = None
    ) -> None:
        self.granularity = granularity
        self._metrics = metrics or {}

    def add_metrics(self, metrics: AWSBillingMetrics) -> None:
        """
        Adds billing metrics to the report.

        :param metrics: Billing metrics.
        :type metrics: AWSBillingMetrics
        """
        self._metrics[metrics.id] = metrics

    def get_metrics(self, id: str) -> AWSBillingMetrics:
        """
        Get billing metrics for an EC2 instance with the given ID.

        :param id: ID of the instance that is associated with the billing metrics.
        :type id: str
        :return: The associated billing metrics.
        :rtype: AWSBillingMetrics
        """
        return self._metrics[id] if id in self._metrics else \
            AWSBillingMetrics(id, self.granularity.period(), None, None, None)
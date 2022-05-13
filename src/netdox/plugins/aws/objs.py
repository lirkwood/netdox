from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from dateutil.tz import tzutc
from enum import Enum
from functools import cache, total_ordering
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
    COMINED_BILLING_DESC: str = 'Billing for EC2 instance + all volumes.'
    """Description for combined billing fragment."""
    INSTANCE_BILLING_DESC: str = 'Billing for EC2 instance.'
    """Description for instance billing fragment."""
    VOLUME_BILLING_DESC: str = 'Billing for all volumes attached to this instance.'
    """Description for volume billing fragment."""
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
    def volumeBilling(self) -> AWSBillingMetrics:
        """
        Returns a billing metrics object for the bills incurred by
        volumes attached to this instance.

        :return: Billing metrics.
        :rtype: AWSBillingMetrics
        """
        billing = AWSBillingMetrics(self.billing.period, 0, 0, 0)
        for volume in self.volumes.values():
            billing = billing + volume.get_billing(billing.period)
        return billing

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
                psml.Property('mount_path', path, 'Mount Path')
            ]) for count, (path, volume) in enumerate(self.volumes.items())
        ]

    @property
    def psmlBody(self) -> list[psml.Section]:
        volumeBilling = self.volumeBilling
        combinedBilling = self.billing + volumeBilling
        return [
            psml.Section('body', fragments = [
                self.psmlGeneral, 
                self.psmlTags,
            ] + self.psmlVolumes),
            psml.Section('billing', fragments = [
                combinedBilling.to_psml('combined_billing', self.COMINED_BILLING_DESC),
                self.billing.to_psml('instance_billing', self.INSTANCE_BILLING_DESC),
                volumeBilling.to_psml('volume_billing', self.VOLUME_BILLING_DESC)
            ])
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
        start = max(self.created, period.start)
        hours = ceil((period.end - start).total_seconds() / 3600)
        size_gb = self.size * self._GiB_TO_GB
        gb_months = size_gb * hours / 730
        
        try:
            cost = gb_months * _get_volume_pricing()[self.type]
        except KeyError:
            raise AttributeError(
                f'Failed to retrieve pricing data for EBSVolume of type: {self.type}')
        return AWSBillingMetrics(period, cost, cost, gb_months)

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

@total_ordering
@dataclass(frozen = True)
class AWSTimePeriod:
    """Object for parsing/serialising to TimePeriod format used in boto3.
    All timezones default to UTC."""
    start: datetime
    """Start of the time period — inclusive."""
    end: datetime
    """End of the time period — exclusive."""
    _start_key: str = 'Start'
    _end_key: str = 'End'

    def __post_init__(self) -> None:
        """
        Adds a UTC timezone to the start and end datetimes if they are naive.
        """
        if self.start.tzinfo is None:
            object.__setattr__(self, 'start', self.start.replace(tzinfo = tzutc()))
        if self.end.tzinfo is None:
            object.__setattr__(self, 'end', self.end.replace(tzinfo = tzutc()))

    def __str__(self) -> str:
        start = self.start.isoformat(timespec = 'seconds')
        end = self.end.isoformat(timespec = 'seconds')
        return f'From {start} to {end}'

    def __eq__(self, other) -> bool:
        return (other.start == self.start) & (other.end == self.end)

    def __lt__(self, other) -> bool:
        return (other.start - other.end) < (self.start - self.end)

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

now = datetime.now()
FORTNIGHT = AWSTimePeriod(now - timedelta(weeks = 2), now)
"""AWSTimePeriod representing 2 weeks/14 days (maximum billing period)."""
    
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
    period: AWSTimePeriod
    """The time period over which the metrics were measured."""
    AmortizedCost: float
    """Unblended cost combined with amortized reservation cost."""
    UnblendedCost: float
    """Usage costs charged during the relevant period."""
    UsageQuantity: float
    """Amount the associated resource was used during the relevant period."""
    METRICS: tuple[str, str, str] = (
        'AmortizedCost', 
        'UnblendedCost',
        'UsageQuantity'
    )
    """The names of the billing metrics this class stores."""

    def __post_init__(self) -> None:
        """
        Ensures that all the float fields are of the correct type.
        """
        object.__setattr__(self, 'AmortizedCost', 
            float(self.AmortizedCost) if self.AmortizedCost is not None else 0.0)
        object.__setattr__(self, 'UnblendedCost', 
            float(self.UnblendedCost) if self.UnblendedCost is not None else 0.0)
        object.__setattr__(self, 'UsageQuantity', 
            float(self.UsageQuantity) if self.UsageQuantity is not None else 0.0)

    def to_psml(self, fragment_id: str = 'billing', description: str = None) -> psml.PropertiesFragment:
        """
        Serialises this object to PSMl.

        :param fragment_id: ID to give the returned properties-fragment, defaults to 'billing'
        :type fragment_id: str, optional
        :param description: Plain english description of what this is billing for.
        :type billed_odescriptionbjects: str, optional
        :return: A properties-fragment object describing the billing metrics.
        :rtype: psml.PropertiesFragment
        """
        amortized = str(round(self.AmortizedCost, 2)) if self.AmortizedCost else 'None'
        unblended = str(round(self.UnblendedCost, 2)) if self.UnblendedCost else 'None'
        usage = str(round(self.UsageQuantity, 2)) if self.UsageQuantity else 'None'

        return psml.PropertiesFragment(fragment_id, [
            psml.Property('period', str(self.period), 'Billing Period'),
            psml.Property('amortized_cost', amortized, 'Amortized Cost (USD)'),
            psml.Property('unblended_cost', unblended, 'Unblended Cost (USD)'),
            psml.Property('usage', usage, 'Usage Quantity')
        ] + [psml.Property('desc', description, 'Description')] 
            if description is not None else []
        )

    def __add__(self, other: AWSBillingMetrics) -> AWSBillingMetrics:
        if self.period != other.period: raise AttributeError(
            'Cannot add metrics with different periods.')

        return AWSBillingMetrics(
            self.period, 
            self.AmortizedCost + other.AmortizedCost,
            self.UnblendedCost + other.UnblendedCost,
            self.UsageQuantity + other.UsageQuantity
        )

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

    def add_metrics(self, resource_id: str, metrics: AWSBillingMetrics) -> None:
        """
        Adds billing metrics to the report.

        :param resource_id: ID of the resource these billing metrics are associated with.
        :type resource_id: str
        :param metrics: Billing metrics.
        :type metrics: AWSBillingMetrics
        """
        self._metrics[resource_id] = metrics

    def get_metrics(self, id: str) -> AWSBillingMetrics:
        """
        Get billing metrics for an EC2 instance with the given ID.

        :param id: ID of the instance that is associated with the billing metrics.
        :type id: str
        :return: The associated billing metrics.
        :rtype: AWSBillingMetrics
        """
        return self._metrics[id] if id in self._metrics else \
            AWSBillingMetrics(self.granularity.period(), 0, 0, 0)
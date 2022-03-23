from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import Enum
from netdox import Network, DefaultNode, psml
from typing import Iterable, Optional

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

    @property
    def psmlInstanceinf(self) -> psml.PropertiesFragment:
        """
        Instanceinf fragment of EC2Instance Node document.

        :return: A *properties-fragment* bs4 tag.
        :rtype: Tag
        """
        return psml.PropertiesFragment('instanceinf', [
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
            psml.Property('tag', value, tag) 
            for tag, value in self.tags.items()
        ])

    @property
    def psmlBody(self) -> list[psml.Section]:
        return [
            psml.Section('body', fragments = [
                self.psmlInstanceinf, self.billing.to_psml(), self.psmlTags
            ])
        ]

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
        return (f'From {start} to {end}')

    def to_dict(self) -> dict[str, str]:
        """
        Returns a dictionary representing this object, usable in boto3 calls.
        """
        return {
            self._start_key: self.start.strftime('%Y-%m-%dT%H:%M:%SZ'),
            self._end_key: self.end.strftime('%Y-%m-%dT%H:%M:%SZ')
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
        amortized = round(self.AmortizedCost, 2) if self.AmortizedCost is not None else 'None'
        unblended = round(self.UnblendedCost, 2) if self.UnblendedCost is not None else 'None'
        usage = round(self.UsageQuantity, 2) if self.UsageQuantity is not None else 'None'

        return psml.PropertiesFragment('billing', [
            psml.Property('period', str(self.period), 'Billing Period'),
            psml.Property('amortized_cost', amortized, 'Amortized Cost (USD)'),
            psml.Property('unblended_cost', unblended, 'Unblended Cost (USD)'),
            psml.Property('usage', usage, 'Usage Quantity')
        ])
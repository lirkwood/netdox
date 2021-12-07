"""
This module contains some essential helper classes.
"""
from __future__ import annotations
from dataclasses import dataclass

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Iterable, Iterator, Optional, no_type_check

from bs4 import BeautifulSoup
from lxml import etree
from netdox import iptools, pageseeder, utils

logger = logging.getLogger(__name__)

#################
# Location Data #
#################

class Locator:
    """
    A helper class for Network.
    Holds the location data for NetworkObjects.
    """
    location_map: dict
    location_pivot: dict

    def __init__(self) -> None:
        try:
            with open(utils.APPDIR+ 'cfg/locations.json', 'r') as stream:
                self.location_map = json.load(stream)
        except Exception:
            self.location_map = {}
        self.location_pivot = {}

        for location in self.location_map:
            for subnet in self.location_map[location]:
                self.location_pivot[subnet] = location

    def __iter__(self) -> Iterator[str]:
        yield from self.location_map.keys()

    def locate(self, ip_set: Iterable) -> Optional[str]:
        """
        Returns a location for an ip or set of ips, or None if there is no determinable location.
        Locations are decided based on the content of the ``locations.json`` config file (for more see :ref:`config`)

        :param ip_set: An Iterable object containing IPv4 addresses in CIDR format as strings
        :type ip_set: Iterable
        :return: The location, as it appears in ``locations.json``, or None if one location exactly could not be assigned.
        :rtype: str
        """
        # sort every declared subnet that matches one of ips by mask size
        matches: dict[int, list[str]] = {}
        for subnet in ip_set:
            for match in self.location_pivot:
                if iptools.subn_contains(match, subnet):
                    mask = int(match.split('/')[-1])
                    if mask not in matches:
                        matches[mask] = []
                    matches[mask].append(self.location_pivot[match])

        matches = dict(sorted(matches.items(), reverse=True))

        # first key when keys are sorted by descending size is largest mask
        try:
            largest = matches[list(matches.keys())[0]]  #@IgnoreException
            largest = list(dict.fromkeys(largest))
            # if multiple unique locations given by equally specific subnets
            if len(largest) > 1:
                return None
            else:
                # use most specific match for location definition
                return largest[0]
        # if no subnets
        except IndexError:
            return None
    

###############
# DNS Records #
###############

class RecordType(Enum):
    A = 0
    PTR = 1
    CNAME = 2
    NAT = 3

class RecordSet:
    """Container for DNS records of a specific type."""
    record_type: RecordType
    """Enum containing the resource record type this object holds."""
    records: set
    """Set of 2-tuples containing a record value and the plugin name that provided it."""

    ## dunder methods

    def __init__(self, type: str) -> None:
        self.record_type = RecordType[type]
        self.records = set()

    def __iter__(self) -> Iterator[str]:
        yield from self.names

    def __ior__(self, recordset: RecordSet) -> RecordSet:
        self.records.__ior__(recordset.records)
        return self

    ## properties

    @property
    def names(self) -> list[str]:
        """
        Returns a list of the record values in this set

        :return: A list record values as strings
        :rtype: list[str]
        """
        return [value for value, _ in self.records]
    
    ## methods

    def add(self, value: str, source: str) -> None:
        self.records.add((value.lower().strip(), source))

    def items(self) -> Iterator[tuple[str, str]]:
        yield from self.records


#################
# JSON Encoding #
#################

class JSONEncoder(json.JSONEncoder):
    """
    JSON Encoder compatible with sets and datetime objects
    """
    def default(self, obj):
        """
        :meta private:
        """
        if isinstance(obj, set):
            return sorted(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, RecordSet):
            return obj.records
        else:
            return super().default(obj)


################
# Daily Report #
################

class Report:
    """
    A report on the changes in the network relative to the last refresh.
    Can be serialised to PSML.
    """
    sections: list[str]
    """A list of section elements to display in the report."""

    def __init__(self) -> None:
        self.sections = []

    def addSection(self, section: str) -> None:
        """
        Adds a psml *section* tag to the report, if it is valid.

        :param section: The section tag to add.
        :type section: str
        """
        try:
            etree.XMLSchema(file = utils.APPDIR + 'src/psml.xsd').assertValid(
                etree.fromstring(bytes(section, 'utf-8')))
        except Exception:
            logger.warning(f'Failed to add invalid PSML section to report.')
            logger.debug(section)
        else:
            self.sections.append(section)

    def writeReport(self) -> None:
        """
        Generates a report from the supplied sections in ``self.report``.
        """
        with open(utils.APPDIR+ 'src/templates/report.psml', 'r') as stream:
            report = BeautifulSoup(stream.read(), 'xml')

        for tag in self.sections:
            report.document.append(BeautifulSoup(tag, 'xml'))

        with open(utils.APPDIR+ 'out/report.psml', 'w') as stream:
            stream.write(str(report))


################
# Label Helper #
################

class LabelDict(dict):
    """
    Container for the labels applied to documents on PageSeeder.
    Behaves like a defaultdict with a 'default_factory' of *set*.

    Maps document docids to a set of labels.
    """
    default_factory = set

    def __getitem__(self, key: str) -> set[str]:
        return super().__getitem__(key)

    def __missing__(self, key) -> set:
        self[key] = self.default_factory()
        return self[key]

    @classmethod
    def from_pageseeder(cls) -> LabelDict:
        """
        Instantiates a LabelManager from the labels on PageSeeder.

        :return: An instance of this class.
        :rtype: LabelManager
        """
        try:
            all_uris = json.loads(
                pageseeder.get_uris(
                    pageseeder.uri_from_path('website'), 
                    {
                        'relationship': 'descendants',
                        'type': 'file'
                    }
                )
            )
        except Exception:
            logger.error('Failed to retrieve URI labels from PageSeeder.')
            all_uris = {'uris':[]}
        finally:
            return cls({ 
                uri['docid']: set(uri['labels'] if 'labels' in uri else []) 
                for uri in all_uris['uris'] if 'docid' in uri
            })


#######################
# Organization Helper #
#######################

@dataclass
class Organization:
    name: str
    """Name of the organization."""
    uriid: str
    """URIID of the organization document."""
    contact_name: str
    """Full name of the organization contact."""
    contact_email: str
    """Email address of the organization contact."""
    contact_phone: str
    """Phone number of the organization contact."""

    @classmethod
    @no_type_check
    def from_psml(cls, psml: str) -> Organization:
        tree = etree.fromstring(psml)
        details = tree.find("section[@id = 'details']/properties-fragment")
        try:
            attrs = [
                tree.find("section[@id = 'title']/fragment/heading").text,
                tree.get('id'),
                details.find("property[@name = 'admin-name']").get('value'),
                details.find("property[@name = 'admin-email']").get('value'),
                details.find("property[@name = 'admin-phone']").get('value')
            ]
        except AttributeError:
            raise ValueError('Failed to parse essential attribute from PSML.')
        else:
            return cls(*[str(attr) for attr in attrs])
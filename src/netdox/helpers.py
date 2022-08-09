"""
This module contains some essential helper classes.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

import json
import logging
import os
from typing import Iterable, Iterator, Optional, no_type_check

from bs4 import BeautifulSoup
from lxml import etree
from netdox import iptools, pageseeder, utils, psml

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

    def __init__(self, locations: dict[str, set[str]]) -> None:
        self.location_map = locations
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
        if isinstance(ip_set, str) and iptools.valid_ip(ip_set):
            ip_set = [ip_set]
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
    logs: str
    """A string containing warning+ logs that occurred 
    while running the refresh for this report."""
    DEFAULT_OUTPATH: str = os.path.join(utils.APPDIR, 'out', 'report.psml')
    """Absolute path to the default serialisation location of this object."""

    def __init__(self) -> None:
        self.sections = []
        self.logs = ''

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

    def writeReport(self, path: str = None) -> None:
        """
        Generates a report from the supplied sections in ``self.report``.

        :param path: Path to write the file to, 
        defaults to ``out/report.psml`` in the app directory.
        :type path: str, optional
        """
        with open(utils.APPDIR+ 'src/templates/report.psml', 'r') as stream:
            report = BeautifulSoup(stream.read(), 'xml')

        logs = report.new_tag('preformat')
        logs.string = self.logs
        report.find('fragment', id = 'logs').append(logs)

        for tag in self.sections:
            report.document.append(BeautifulSoup(tag, 'xml'))

        with open(path or self.DEFAULT_OUTPATH, 'w') as stream:
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

###################
# Counting Helper #
###################

class CountedFacets(Enum):
    DNSObject = 'dnsobject'
    Node = 'node'
    DNSLink = 'dnslink'
    NATLink = 'natlink'

@dataclass(frozen = True)
class Counter:
    _counts: dict[CountedFacets, int]
    """Maps facet to its counted occurences."""
    DEFAULT_COUNTS = {facet: 0 for facet in CountedFacets}
    """Default dict of counts."""

    def __init__(self) -> None:
        object.__setattr__(self, '_counts', dict(self.DEFAULT_COUNTS))

    def inc_facet(self, facet: CountedFacets) -> int:
        """
        Increments the count of a facet.

        :param facet: Facet to increment the count for.
        :type facet: Any
        :return: The new count for the facet.
        :rtype: int
        """
        try:
            count = self._counts[facet] + 1
        except KeyError:
            count = 1
        finally:
            self._counts[facet] = count
            return count

    def dec_facet(self, facet: CountedFacets) -> int:
        """
        Decrements the count of a facet.
        If count is zero then the count will be unchanged.

        :param facet: Facet to decrement the count for.
        :type facet: Any
        :return: The new count for the facet.
        :rtype: int
        """
        try:
            count = self._counts[facet] - 1
            if count < 0: count = 0
        except KeyError:
            count = 0
        finally:
            self._counts[facet] = count
            return count

    @property
    def counts(self) -> dict[CountedFacets, int]:
        """Maps facets to their current counts."""
        return self.DEFAULT_COUNTS | self._counts

    def generate_report(self) -> psml.Section:
        counts = self.counts
        return psml.Section('counts', 'Counted Facets', [
            psml.PropertiesFragment(f'{facet.value}_counts', [
                psml.Property('facet', facet.name, 'Facet Name'),
                psml.Property(facet.name, str(counts[facet]), 'Value')
            ]) for facet in counts
        ])
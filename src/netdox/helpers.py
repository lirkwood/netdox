"""
This module contains some essential helper classes.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from enum import Enum
from typing import Iterable, Iterator
import logging
from lxml import etree
from collections import defaultdict

from bs4 import BeautifulSoup, Tag
from netdox import iptools, pageseeder, psml, utils
from netdox import base, nwobjs

logger = logging.getLogger(__name__)

###################
# Location Helper #
###################

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

    def locate(self, ip_set: Iterable) -> str:
        """
        Returns a location for an ip or set of ips, or None if there is no determinable location.
        Locations are decided based on the content of the ``locations.json`` config file (for more see :ref:`config`)

        :param ip_set: An Iterable object containing IPv4 addresses in CIDR format as strings
        :type ip_set: Iterable
        :return: The location, as it appears in ``locations.json``, or None if one location exactly could not be assigned.
        :rtype: str
        """
        # sort every declared subnet that matches one of ips by mask size
        matches = {}
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
# PSML Helper #
###############

class PSMLWriter:
    """
    Serialises a NetworkObject to PSML.
    """
    doc: BeautifulSoup
    body: BeautifulSoup
    footer: list[Tag]

    def serialiseSet(self, nwobjc: base.NetworkObjectContainer) -> None:
        """
        Serialises a set of NetworkObjects.

        :param nwobjc: An iterable object containing NetworkObjects.
        :type nwobjc: NetworkObjectContainer
        """
        for nwobj in nwobjc:
            self.serialise(nwobj)

    def serialise(self, nwobj: base.NetworkObject) -> None:
        """
        Serialises a NetworkObject to PSML and writes to disk.

        :param nwobj: The object to serialise to PSML.
        :type nwobj: NetworkObject
        """
        if isinstance(nwobj, nwobjs.Domain):
            self.domainBody(nwobj)
        elif isinstance(nwobj, nwobjs.IPv4Address):
            self.ipBody(nwobj)
        elif isinstance(nwobj, nwobjs.Node):
            self.nodeBody(nwobj)
        else:
            self.doc = None
            raise NotImplementedError

        self.doc.find('labels').string = ','.join(nwobj.labels)

        self.footer = self.doc.find(id = 'footer')
        for tag in nwobj.psmlFooter:
            self.footer.append(tag)

        # Add search octet fragment to doc footer but not nwobj
        search_octets = []
        for ip in nwobj.ips:
            octets = ip.split('.')
            search_octets.append(octets[-1])
            search_octets.append('.'.join(octets[-2:]))
        psml.PropertiesFragment(id = 'for-search', properties = [
            psml.Property(name = 'octets', title = 'Octets for search', 
                value = ', '.join(search_octets) if search_octets else '')
        ], attrs = {'labels':'s-hide-content'})

        dir = os.path.dirname(nwobj.outpath)
        if not os.path.exists(dir):
            os.makedirs(dir)

        with open(nwobj.outpath, 'w', encoding = 'utf-8') as stream:
            stream.write(str(self.doc))
    
    def domainBody(self, domain: nwobjs.Domain) -> None:
        """
        Populates the *body* section of a Domain's output PSML

        :param domain: The Domain object to parse into PSML
        :type domain: Domain
        """
        self.doc = psml.populate(psml.DOMAIN_TEMPLATE, domain)
        self.body = self.doc.find(id = 'records')

        if domain.node:
            self.doc.find('properties-fragment', id = 'header').append(psml.Property(
                name = 'node',
                title = 'Node',
                value = psml.XRef(docid = domain.node.docid)
            ))
        else:
            self.doc.find('properties-fragment', id = 'header').append(psml.Property(
                name = 'node',
                title = 'Node',
                value = '—'
            ))

        for frag in psml.recordset2pfrags(
            recordset = domain.records['A'],
            id_prefix = 'A_record_',
            docid_prefix = '_nd_ip_',
            p_name = 'ipv4',
            p_title = 'A Record'
        ):  self.body.append(frag)

        for frag in psml.recordset2pfrags(
            recordset = domain.records['CNAME'],
            id_prefix = 'CNAME_record_',
            docid_prefix = '_nd_domain_',
            p_name = 'domain',
            p_title = 'CNAME Record'
        ):  self.body.append(frag)
    
    def ipBody(self, ip: nwobjs.IPv4Address) -> None:
        """
        Populates the *body* section of a IPv4Address' output PSML

        :param ip: The IPv4Address object to parse into PSML
        :type ip: IPv4Address
        """
        self.doc = psml.populate(psml.IPV4ADDRESS_TEMPLATE, ip)
        self.body = self.doc.find(id = 'records')

        if ip.nat:
            self.doc.find('properties-fragment', id = 'header').append(psml.Property(
                name = 'nat',
                title = 'NAT Destination',
                value = psml.XRef(docid = f'_nd_ip_{ip.nat.replace(".","_")}')
            ))
        else:
            self.doc.find('properties-fragment', id = 'header').append(psml.Property(
                name = 'nat',
                title = 'NAT Destination',
                value = '—'
            ))

        if ip.node:
            self.doc.find('properties-fragment', id = 'header').append(psml.Property(
                name = 'node',
                title = 'Node',
                value = psml.XRef(docid = ip.node.docid)
            ))
        else:
            self.doc.find('properties-fragment', id = 'header').append(psml.Property(
                name = 'node',
                title = 'Node',
                value = '—'
            ))

        if ip.unused:
            ip.labels.add('unused')

        for frag in psml.recordset2pfrags(
            recordset = ip.records['PTR'],
            id_prefix = 'PTR_record_',
            docid_prefix = '_nd_domain_',
            p_name = 'domain',
            p_title = 'PTR Record'
        ):  self.body.append(frag)

        psml.PropertiesFragment(id = 'implied_ptr', properties = [
            psml.Property(
                    name = 'domain',
                    title = 'Implied PTR Record',
                    value = psml.XRef(docid = f'_nd_domain_{domain.replace(".","_")}')
                )
            for domain in ip.backrefs['A']
        ])

    def nodeBody(self, node: nwobjs.Node) -> None:
        """
        Populates the *body* section of a Node's output PSML

        :param node: The Node object to parse into PSML
        :type node: Node
        """
        self.doc = psml.populate(psml.NODE_TEMPLATE, node)
        self.body = self.doc.find(id = 'body')

        self.doc.find(attrs={'name':'location'})['value'] = node.location

        for tag in node.psmlBody:
            self.body.append(tag)
        self.body.unwrap()

        domains = self.doc.new_tag('properties-fragment', id = 'domains')
        for domain in node.domains:
            if domain in node.network.domains:
                domains.append(psml.Property(
                    name = 'domain',
                    title = 'Domain',
                    value = psml.XRef(docid = f'_nd_domain_{domain.replace(".","_")}')
                ))
            else:
                domains.append(psml.Property(
                    name = 'domain',
                    title = 'Domain',
                    value = domain
                ))

        ips = self.doc.new_tag('properties-fragment', id = 'ips')
        for ip in node.ips:
            if ip in node.network.ips:
                ips.append(psml.Property(
                    name = 'ipv4',
                    title = 'Public IP' if iptools.public_ip(ip) else 'Private IP',
                    value = psml.XRef(docid = f'_nd_ip_{ip.replace(".","_")}')
                ))
            else:
                ips.append(psml.Property(
                    name = 'ipv4',
                    title = 'Public IP' if iptools.public_ip(ip) else 'Private IP',
                    value = ip
                ))

        header = self.doc.find('section', id = 'header')
        header.append(domains)
        header.append(ips)

####################
# RecordSet Helper #
####################

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


######################
# JSONEncoder Helper #
######################

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


#################
# Report Helper #
#################

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
        :type section: Tag
        """
        if etree.XMLSchema(file = utils.APPDIR + 'src/psml.xsd').validate(
            etree.fromstring(bytes(section, 'utf-8'))
        ):
            self.sections.append(section)

    def writeReport(self) -> None:
        """
        Generates a report from the supplied sections in ``self.report``.
        """
        with open(utils.APPDIR+ 'src/templates/report.psml', 'r') as stream:
            report = BeautifulSoup(stream.read(), 'xml')

        for tag in self.sections:
            report.document.append(tag)

        with open(utils.APPDIR+ 'out/report.psml', 'w') as stream:
            stream.write(str(report))


################
# Label Helper #
################

class LabelDict(defaultdict):
    """
    Container for the labels applied to documents on PageSeeder.
    Behaves like a defaultdict with a 'default_factory' of *set*.

    Maps document docids to a set of labels.
    """
    default_factory = set

    def __getitem__(self, key: str) -> set[str]:
        return super().__getitem__(key)

    def __init__(self, *args, **kwargs) -> None:
        """
        Dictionary constructor.
        """
        super().__init__(set, *args, **kwargs)

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
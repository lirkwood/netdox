"""
This module contains some helper classes that are essential to the other classes in the objs package.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Iterable, Iterator
from enum import Enum

from bs4 import BeautifulSoup, Tag

from netdox import iptools, psml, utils
from netdox.objs import base, nwobjs

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
        octetFrag = Tag(is_xml=True, name='properties-fragment', attrs={'id':'for-search', 'labels':'s-hide-content'})
        octetFrag.append(psml.newprop(
            name = 'octets', title = 'Octets for search', value = ', '.join(search_octets)
        ))
        self.footer.append(octetFrag)

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
            self.doc.find('properties-fragment', id = 'header').append(psml.newxrefprop(
                name = 'node',
                title = 'Node',
                ref = domain.node.docid
            ))
        else:
            self.doc.find('properties-fragment', id = 'header').append(psml.newprop(
                name = 'node',
                title = 'Node',
                value = '—'
            ))

        if 'uri' in utils.roles()[domain.role]:
            self.doc.find(title='DNS Role').xref['uriid'] = utils.roles()[domain.role]['uri']
        else:
            self.doc.find(title='DNS Role').xref['docid'] = '_nd_role_'+ domain.role

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
            self.doc.find('properties-fragment', id = 'header').append(psml.newxrefprop(
                name = 'nat',
                title = 'NAT Destination',
                ref = f'_nd_ip_{ip.nat.replace(".","_")}'
            ))
        else:
            self.doc.find('properties-fragment', id = 'header').append(psml.newprop(
                name = 'nat',
                title = 'NAT Destination',
                value = '—'
            ))

        if ip.node:
            self.doc.find('properties-fragment', id = 'header').append(psml.newxrefprop(
                name = 'node',
                title = 'Node',
                ref = ip.node.docid
            ))
        else:
            self.doc.find('properties-fragment', id = 'header').append(psml.newprop(
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

        impliedfrag = self.doc.new_tag('properties-fragment', id = 'implied_ptr')
        for domain in ip.backrefs['A']:
            impliedfrag.append(psml.newxrefprop(
                name = 'domain',
                title = 'Implied PTR Record',
                ref = f'_nd_domain_{domain.replace(".","_")}'
            ))
        self.body.append(impliedfrag)

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
                domains.append(psml.newxrefprop(
                    name = 'domain',
                    title = 'Domain',
                    ref = f'_nd_domain_{domain.replace(".","_")}'
                ))
            else:
                domains.append(psml.newprop(
                    name = 'domain',
                    title = 'Domain',
                    value = domain
                ))

        ips = self.doc.new_tag('properties-fragment', id = 'ips')
        for ip in node.ips:
            if ip in node.network.ips:
                ips.append(psml.newxrefprop(
                    name = 'ipv4',
                    title = 'Public IP' if iptools.public_ip(ip) else 'Private IP',
                    ref = f'_nd_ip_{ip.replace(".","_")}'
                ))
            else:
                ips.append(psml.newprop(
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

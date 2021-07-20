from __future__ import annotations

import json
import os
from datetime import datetime
from typing import TYPE_CHECKING, Iterable, Iterator

import iptools
from bs4 import BeautifulSoup

from psml import *
from .domains import Domain
from .ips import IPv4Address
from .nodes import Node

if TYPE_CHECKING:
    from .base import NetworkObject, NetworkObjectContainer
    

##################
# Helper Classes #
##################

class Locator:
    """
    A helper class for Network.
    Holds the location data for NetworkObjects.
    """
    location_map: dict
    location_pivot: dict

    def __init__(self) -> None:
        try:
            with open('src/locations.json', 'r') as stream:
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
            largest = matches[list(matches.keys())[0]]
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


class PSMLWriter:
    doc: BeautifulSoup
    body: BeautifulSoup

    def serialiseSet(self, nwobjc: NetworkObjectContainer, dir: str) -> None:
        """
        Serialises a set of NetworkObjects using some default settings.

        :param nwobjc: An iterable object containing NetworkObjects.
        :type nwobjc: NetworkObjectContainer
        :param dir: The directory to output the PSML files to.
        :type dir: str
        """
        if nwobjc.objectType == 'ips':
            for ip in nwobjc:
                self.serialise(ip, f'{dir}/{ip.subnet.replace("/","_")}/{ip.docid}.psml')
        else:
            for nwobj in nwobjc:
                self.serialise(nwobj, f'{dir}/{nwobj.docid}.psml')

    def serialise(self, nwobj: NetworkObject, path: str) -> None:
        """
        Serialises a NetworkObject to PSML and writes to a given path.

        :param nwobj: The object to serialise to PSML.
        :type nwobj: NetworkObject
        :param path: The path to save the output document to.
        :type path: str
        """
        if isinstance(nwobj, Domain):
            self.doc = populate(DOMAIN_TEMPLATE, nwobj)
            self.domainBody(nwobj)
        elif isinstance(nwobj, IPv4Address):
            self.doc = populate(IPV4ADDRESS_TEMPLATE, nwobj)
            self.ipBody(nwobj)
        elif isinstance(nwobj, Node):
            self.doc = populate(NODE_TEMPLATE, nwobj)
            self.nodeBody(nwobj)
        else:
            self.doc = None
            raise NotImplementedError

        if nwobj.psmlFooter:
            self.doc.find(id = 'footer').replace_with(nwobj.psmlFooter)

        dir = os.path.dirname(path)
        if not os.path.exists(dir):
            os.makedirs(dir)

        with open(path, 'w') as stream:
            stream.write(self.doc.prettify())
    
    def domainBody(self, domain: Domain) -> None:
        """
        Populates the *body* section of a Domain's output PSML

        :param domain: The Domain object to parse into PSML
        :type domain: Domain
        """
        self.doc = populate(DOMAIN_TEMPLATE, domain)
        self.body = self.doc.find(id = 'records')

        if domain.node:
            self.doc.find(id = 'info').append(propertyXref(
                doc = self.doc,
                p_name = 'node',
                p_title = 'Node',
                docid = domain.node.docid
            ))

        for frag in recordset2pfrags(
            doc = self.doc,
            recordset = domain._private_ips,
            id_prefix = 'private_ip_',
            docid_prefix = '_nd_ip_',
            p_name = 'ipv4',
            p_title = 'Private IP'
        ):  self.body.append(frag)

        for frag in recordset2pfrags(
            doc = self.doc,
            recordset = domain._public_ips,
            id_prefix = 'public_ip_',
            docid_prefix = '_nd_ip_',
            p_name = 'ipv4',
            p_title = 'Public IP'
        ):  self.body.append(frag)

        for frag in recordset2pfrags(
            doc = self.doc,
            recordset = domain._cnames,
            id_prefix = 'cname_',
            docid_prefix = '_nd_domain_',
            p_name = 'ipv4',
            p_title = 'CNAME'
        ):  self.body.append(frag)
    
    def ipBody(self, ip: IPv4Address) -> None:
        """
        Populates the *body* section of a IPv4Address' output PSML

        :param ip: The IPv4Address object to parse into PSML
        :type ip: IPv4Address
        """
        self.doc = populate(IPV4ADDRESS_TEMPLATE, ip)
        self.body = self.doc.find(id = 'records')

        if ip.nat:
            self.doc.find(id = 'info').append(propertyXref(
                doc = self.doc,
                p_name = 'nat',
                p_title = 'NAT Destination',
                docid = f'_nd_ip_{ip.nat.replace(".","_")}'
            ))

        if ip.node:
            self.doc.find(id = 'info').append(propertyXref(
                doc = self.doc,
                p_name = 'node',
                p_title = 'Node',
                docid = ip.node.docid
            ))

        for frag in recordset2pfrags(
            doc = self.doc,
            recordset = ip._ptr,
            id_prefix = 'ptr_',
            docid_prefix = '_nd_domain_',
            p_name = 'ptr',
            p_title = 'PTR Record'
        ):  self.body.append(frag)
        impliedfrag = self.doc.new_tag('properties-fragment', id = 'implied_ptr')
        for domain in ip.implied_ptr:
            impliedfrag.append(propertyXref(
                doc = self.doc,
                p_name = 'impliedptr',
                p_title = 'Implied PTR Record',
                docid = f'_nd_domain_{domain.replace(".","_")}'
            ))
        self.body.append(impliedfrag)

    def nodeBody(self, node: Node) -> None:
        """
        Populates the *body* section of a Node's output PSML

        :param node: The Node object to parse into PSML
        :type node: Node
        """
        self.doc = populate(NODE_TEMPLATE, node)
        self.body = self.doc.find(id = 'body')

        for tag in node.psmlBody:
            self.body.append(tag)
        self.body.unwrap()
        
        details = self.doc.find(id = 'details')
        domains = self.doc.new_tag('properties-fragment', id = 'domains')
        for domain in node.domains:
            domains.append(propertyXref(
                doc = self.doc,
                p_name = 'domain',
                p_title = 'Domain',
                docid = f'_nd_domain_{domain.replace(".","_")}'
            ))
        details.append(domains)


class JSONEncoder(json.JSONEncoder):
    """
    JSON Encoder compatible with NetworkObjects, sets, and datetime objects
    """
    def default(self, obj):
        """
        :meta private:
        """
        if isinstance(obj, NetworkObject):
            return obj.__dict__ | {'node': obj.node.docid if hasattr(obj, 'node') and obj.node else None}
        elif isinstance(obj, NetworkObjectContainer):
            return None
        # elif isinstance(obj, Network):
        #     return None
        elif isinstance(obj, set):
            return sorted(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return super().default(obj)

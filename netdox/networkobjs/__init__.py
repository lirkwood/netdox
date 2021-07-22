"""
This module contains the NetworkObject classes used to store the DNS and Node information, their containers, and two helper classes.

The NetworkObject class is an abstract base class subclassed by Domain, IPv4Address, and Node. 
NetworkObjects represent one type of object in the network. 
It could be a unique FQDN found in a managed DNS zone, an IP address one of those domains resolves to, or a Node.
A Node is representative of a single machine / virtualised machine.
When writing plugins for the node stage developers are encouraged to write their own subclass of Node, 
specific to the target of their plugin.
This allows you to define how the Node will behave when it is added to a NodeSet or Network, 
and it's strategy for merging with other Nodes.
"""
from __future__ import annotations

import json
import os

from psml import *
from utils import DEFAULT_CONFIG

from .base import *
from .containers import *
from .objects import *

######################
# The Network Object #
######################

class Network:
    """
    Container for sets of network objects.
    """
    domains: DomainSet
    """A NetworkObjectContainer for the Domains in the network."""
    ips: IPv4AddressSet
    """A NetworkObjectContainer for the IPv4Addresses in the network."""
    nodes: NodeSet
    """A NetworkObjectContainer for the Nodes in the network."""
    config: dict
    """The currently loaded config from :ref:`utils`."""

    def __init__(self, 
            domains: DomainSet = None, 
            ips: IPv4AddressSet = None, 
            nodes: NodeSet = None,
            config: dict = None,
            roles: dict = None
        ) -> None:
        """
        Instantiate a Network object.

        :param domains: A DomainSet to include in the network, defaults to None
        :type domains: DomainSet, optional
        :param ips: A IPv4AddressSet to include in the network, defaults to None
        :type ips: IPv4AddressSet, optional
        :param nodes: A NodeSet to include in the network, defaults to None
        :type nodes: NodeSet, optional
        :param config: A dictionary of config values like that returned by ``utils.config()``, defaults to None
        :type config: dict, optional
        :param roles: A dictionary of role configuration values to pass to the DomainSet of the network, defaults to None
        :type roles: dict, optional
        """

        self.domains = domains or DomainSet(network = self, roles = roles)
        self.ips = ips or IPv4AddressSet(network = self)
        self.nodes = nodes or NodeSet(network = self)
        
        self.config = config or DEFAULT_CONFIG
        self.locator = Locator()
        self.writer = PSMLWriter()

    def __contains__(self, object: str) -> bool:
        return (
            self.domains.__contains__(object) or
            self.ips.__contains__(object) or
            self.nodes.__contains__(object)
        )

    def add(self, object: NetworkObject) -> None:
        """
        Calls the *add* method on one of the three NetworkObjectContainers in this network. based on the class inheritance of *object*.

        :param object: An object to add to one of the three NetworkObjectContainers.
        :type object: NetworkObject
        """
        if isinstance(object, Domain):
            self.domains.add(object)
        elif isinstance(object, IPv4Address):
            self.ips.add(object)
        elif isinstance(object, Node):
            self.nodes.add(object)

    def replace(self, identifier: str, object: NetworkObject) -> None:
        """
        Replace a NetworkObject in the network
        """
        if isinstance(object, Domain):
            self.domains.replace(identifier, object)
        elif isinstance(object, IPv4Address):
            self.ips.replace(identifier, object)
        elif isinstance(object, Node):
            self.nodes.replace(identifier, object)

    def addSet(self, object_set: NetworkObjectContainer) -> None:
        """
        Add a set of network objects to the network

        2do: Implement merge in NetworkObjectContainer ABC

        :param object_set: An NetworkObjectContainer to add to the network
        :type object_set: NetworkObjectContainer
        """
        if isinstance(object_set, DomainSet):
            object_set.network = self
            self.domains = object_set
        elif isinstance(object_set, IPv4AddressSet):
            object_set.network = self
            self.ips = object_set
        elif isinstance(object_set, NodeSet):
            object_set.network = self
            self.nodes = object_set

    @property
    def records(self) -> dict:
        """
        Returns a dictionary of the defined links between domains and IPs

        :return: A dictionary with 'forward' and 'reverse' keys mapped to a dictionary of forward/reverse DNS records.
        :rtype: dict
        """
        return {
            'forward': {domain.name: domain.destinations for domain in self.domains},
            'reverse': {ip.addr: ip.ptr for ip in self.ips}
        }

    @property
    def implied_records(self) -> dict:
        """
        Returns a dictionary of the implied links between domains and IPs

        :return: A dictionary with 'forward' and 'reverse' keys mapped to a dictionary of forward/reverse implied DNS records.
        :rtype: dict
        """
        return {
            'forward': {ip.addr: ip.domains for ip in self.ips},
            'reverse': {domain.name: domain.iplinks for domain in self.domains}
        }

    def discoverImpliedLinks(self) -> None:
        """
        Populates the implied link attributes for the Domain and IPv4Address objects in the Network.
        Also sets their Node attributes where possible.
        """
        for domain, ips in self.records['forward'].items():
            for ip in ips:
                if ip in self.ips and domain not in self.ips[ip].ptr:
                    self.ips[ip].implied_ptr.add(domain)

        for ip, domains in self.records['reverse'].items():
            for domain in domains:
                if domain in self.domains and ip not in self.domains[domain].ips:
                    self.domains[domain].implied_ips.add(ip)

        for node in self.nodes:
            for ip in node.ips:
                if ip in self.ips and not self.ips[ip].node:
                    self.ips[ip].node = node
                    
            for domain in node.domains:
                if domain in self.domains and not self.domains[domain].node:
                    self.domains[domain].node = node
    
    def setFromJSON(self, path: str) -> None:
        """
        Loads a NetworkObjectContainer from a JSON file.

        :param path: Path to the JSON file.
        :type path: str
        """
        with open(path, 'r') as stream:
            setDict = json.load(stream)

        if setDict['objectType'] == 'domains':
            self.addSet(DomainSet.from_dict(setDict))
        elif setDict['objectType'] == 'ips':
            self.addSet(IPv4AddressSet.from_dict(setDict))
        elif setDict['objectType'] == 'nodes':
            self.addSet(NodeSet.from_dict(setDict))

    def setToJSON(self, set: str, path: str) -> None:
        """
        Serialises a NetworkObjectContainer to JSON and writes the JSON to a file at *path*.

        :param set: The atribute name of the set to serialise, one of: 'domains', 'ips', or 'nodes'.
        :type set: str
        :param path: The path to write the JSON to.
        :type path: str
        """
        getattr(self, set).to_json(path)

    def setToPSML(self, set: str, dir: str) -> None:
        """
        Serialises a NetworkObjectContainer to PSML and writes the PSML files to *dir*.

        :param set: The atribute name of the set to serialise, one of: 'domains', 'ips', or 'nodes'.
        :type set: str
        :param dir: The directory to output the PSML files to.
        :type dir: str
        """
        self.writer.serialiseSet(getattr(self, set), dir)

    def dumpNetwork(self) -> None:
        """
        Writes the domains, ips, and nodes of a network to their default locations.
        """
        self.setToJSON('domains', 'src/domains.json')
        self.setToJSON('ips', 'src/ips.json')
        self.setToJSON('nodes', 'src/nodes.json')

    def writePSML(self) -> None:
        """
        Writes the domains, ips, and nodes of a network to PSML using ``self.writer``.
        """
        self.setToPSML('domains')
        self.setToPSML('ips')
        self.setToPSML('nodes')


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


###############
# PSML Helper #
###############

class PSMLWriter:
    """
    Serialises a NetworkObject to PSML.
    """
    doc: BeautifulSoup
    body: BeautifulSoup

    def serialiseSet(self, nwobjc: NetworkObjectContainer) -> None:
        """
        Serialises a set of NetworkObjects.

        :param nwobjc: An iterable object containing NetworkObjects.
        :type nwobjc: NetworkObjectContainer
        """
        for nwobj in nwobjc:
            self.serialise(nwobj)

    def serialise(self, nwobj: NetworkObject) -> None:
        """
        Serialises a NetworkObject to PSML and writes to disk.

        :param nwobj: The object to serialise to PSML.
        :type nwobj: NetworkObject
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

        self.footer = self.doc.find(id = 'footer')
        if nwobj.psmlFooter:
            map(self.footer.append, nwobj.psmlFooter)

        dir = os.path.dirname(nwobj.outpath)
        if not os.path.exists(dir):
            os.makedirs(dir)

        with open(nwobj.outpath, 'w') as stream:
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
            self.doc.find(id = 'info').append(newxrefprop(
                name = 'node',
                title = 'Node',
                ref = domain.node.docid
            ))

        for frag in recordset2pfrags(
            recordset = domain._private_ips,
            id_prefix = 'private_ip_',
            docid_prefix = '_nd_ip_',
            p_name = 'ipv4',
            p_title = 'Private IP'
        ):  self.body.append(frag)

        for frag in recordset2pfrags(
            recordset = domain._public_ips,
            id_prefix = 'public_ip_',
            docid_prefix = '_nd_ip_',
            p_name = 'ipv4',
            p_title = 'Public IP'
        ):  self.body.append(frag)

        for frag in recordset2pfrags(
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
            self.doc.find(id = 'info').append(newxrefprop(
                name = 'nat',
                title = 'NAT Destination',
                ref = f'_nd_ip_{ip.nat.replace(".","_")}'
            ))

        if ip.node:
            self.doc.find(id = 'info').append(newxrefprop(
                name = 'node',
                title = 'Node',
                ref = ip.node.docid
            ))

        for frag in recordset2pfrags(
            recordset = ip._ptr,
            id_prefix = 'ptr_',
            docid_prefix = '_nd_domain_',
            p_name = 'ptr',
            p_title = 'PTR Record'
        ):  self.body.append(frag)
        impliedfrag = self.doc.new_tag('properties-fragment', id = 'implied_ptr')
        for domain in ip.implied_ptr:
            impliedfrag.append(newxrefprop(
                name = 'impliedptr',
                title = 'Implied PTR Record',
                ref = f'_nd_domain_{domain.replace(".","_")}'
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

        map(self.body.append, node.psmlBody)
        self.body.unwrap()
        
        details = self.doc.find(id = 'details')
        domains = self.doc.new_tag('properties-fragment', id = 'domains')
        for domain in node.domains:
            domains.append(newxrefprop(
                name = 'domain',
                title = 'Domain',
                ref = f'_nd_domain_{domain.replace(".","_")}'
            ))
        details.append(domains)

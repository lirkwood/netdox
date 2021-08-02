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
import psml
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

    def setToPSML(self, set: str) -> None:
        """
        Serialises a NetworkObjectContainer to PSML and writes the PSML files to *dir*.

        :param set: The atribute name of the set to serialise, one of: 'domains', 'ips', or 'nodes'.
        :type set: str
        """
        self.writer.serialiseSet(getattr(self, set))

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
    footer: list[Tag]

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
            self.domainBody(nwobj)
        elif isinstance(nwobj, IPv4Address):
            self.ipBody(nwobj)
        elif isinstance(nwobj, Node):
            self.nodeBody(nwobj)
        else:
            self.doc = None
            raise NotImplementedError

        self.footer = self.doc.find(id = 'footer')
        if nwobj.psmlFooter:
            for tag in nwobj.psmlFooter:
                self.footer.append(tag)

            search_octets = []
            for ip in nwobj.ips:
                octets = ip.split('.')
                search_octets.append(octets[-1])
                search_octets.append('.'.join(octets[-2:]))
            frag = Tag(is_xml=True, name='fragment')
            frag.append(psml.newprop(
                name = 'octets', title = 'Octets for search', value = ', '.join(search_octets), multiple = 'true'
            ))
            nwobj.psmlFooter.append(frag)
        

        dir = os.path.dirname(nwobj.outpath)
        if not os.path.exists(dir):
            os.makedirs(dir)

        with open(nwobj.outpath, 'w', encoding = 'utf-8') as stream:
            stream.write(str(self.doc))
    
    def domainBody(self, domain: Domain) -> None:
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

        if 'uri' in utils.roles()[domain.role]:
            self.doc.find(title='DNS Role').xref['uriid'] = utils.roles()[domain.role]['uri']
        else:
            roleprop = self.doc.find(title='DNS Role')
            roleprop.xref.decompose()
            roleprop['datatype'] = 'string'
            roleprop['value'] = '—'

        for frag in psml.recordset2pfrags(
            recordset = domain._private_ips,
            id_prefix = 'private_ip_',
            docid_prefix = '_nd_ip_',
            p_name = 'ipv4',
            p_title = 'Private IP'
        ):  self.body.append(frag)

        for frag in psml.recordset2pfrags(
            recordset = domain._public_ips,
            id_prefix = 'public_ip_',
            docid_prefix = '_nd_ip_',
            p_name = 'ipv4',
            p_title = 'Public IP'
        ):  self.body.append(frag)

        for frag in psml.recordset2pfrags(
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
        self.doc = psml.populate(psml.IPV4ADDRESS_TEMPLATE, ip)
        self.body = self.doc.find(id = 'records')

        if ip.nat:
            self.doc.find('properties-fragment', id = 'header').append(psml.newxrefprop(
                name = 'nat',
                title = 'NAT Destination',
                ref = f'_nd_ip_{ip.nat.replace(".","_")}'
            ))

        if ip.node:
            self.doc.find('properties-fragment', id = 'header').append(psml.newxrefprop(
                name = 'node',
                title = 'Node',
                ref = ip.node.docid
            ))

        for frag in psml.recordset2pfrags(
            recordset = ip._ptr,
            id_prefix = 'ptr_',
            docid_prefix = '_nd_domain_',
            p_name = 'ptr',
            p_title = 'PTR Record'
        ):  self.body.append(frag)

        impliedfrag = self.doc.new_tag('properties-fragment', id = 'implied_ptr')
        for domain in ip.implied_ptr:
            impliedfrag.append(psml.newxrefprop(
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
        self.doc = psml.populate(psml.NODE_TEMPLATE, node)
        self.body = self.doc.find(id = 'body')

        for tag in node.psmlBody:
            self.body.append(tag)
        self.body.unwrap()
        
        header = self.doc.find('section', id = 'header')

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
        header.append(domains)
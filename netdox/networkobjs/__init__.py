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
import re

from psml import *

from utils import DEFAULT_CONFIG
from .base import *
from .domains import *
from .ips import *
from .nodes import *
from .utils import *

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
        with open(path, 'w') as stream:
            stream.write(getattr(self, set).to_json())

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
        self.setToPSML('domains', 'out/domains')
        self.setToPSML('ips', 'out/ips')
        self.setToPSML('nodes', 'out/nodes')

"""
This module contains the objects that represent a single computer.
"""
from __future__ import annotations

import logging
import os
import re
from hashlib import sha256
from typing import TYPE_CHECKING, Iterable, Optional, Type

from bs4 import BeautifulSoup
from bs4.element import Tag

from netdox import base, dns, iptools, utils
from netdox.psml import (NODE_TEMPLATE, PropertiesFragment, Property, Section,
                         XRef)

if TYPE_CHECKING:
    from netdox import Network

logger = logging.getLogger(__name__)

class Node(base.NetworkObject):
    """
    A single physical or virtual machine.
    """
    identity: str
    """A string unique to this Node that can always be used to find it."""
    _domains: set[str]
    """A set of domains resolving to this Node."""
    _ips: set[str]
    """A set of IPv4 addresses resolving to this Node."""
    _location: Optional[str]
    """Optional manual location attribute to use instead of the network locator."""
    TEMPLATE = NODE_TEMPLATE
    type: str = 'node'

    ## dunder methods

    def __init__(self, 
            network: Network, 
            name: str, 
            identity: str, 
            domains: Iterable[str], 
            ips: Iterable[str],
            labels: Iterable[str] = None
        ) -> None:
        """
        Constructor.

        :param network: The network this node is in.
        :type network: Network
        :param name: The name for this node.
        :type name: str
        :param identity: A unique identifier for this node.
        :type identity: str
        :param domains: A set of domain names that this node claims resolve to it.
        :type domains: Iterable[str]
        :param ips: A set of IPv4 addresses that this node claims resolve to it.
        :type ips: Iterable[str]
        :param labels: A set of document labels to apply to the resulting 
        PageSeeder document, defaults to None
        :type labels: Iterable[str], optional
        """
        self.identity = identity.lower()
        self._location = None
        super().__init__(network, name, identity, labels)

        self._domains = {d.lower() for d in domains} if domains else set()
        self._ips = set(ips) if ips else set()

    ## abstract properties

    @property
    def psmlBody(self) -> list[Section]:
        """
        Returns a list of section tags to add to the body of this Node's output PSML.

        :return: A list of psml Sections.
        :rtype: list[Section]
        """
        return []

    @property
    def docid(self) -> str:
        return (
            f'_nd_node_{self.type}_' +
            re.sub(utils.docid_invalid_pattern, "_", self.identity)
        )

    @property
    def outpath(self) -> str:
        return os.path.normpath(os.path.join(utils.APPDIR, f'out/nodes/{self.docid}.psml'))

    @property
    def domains(self) -> set[str]:
        return self._domains

    @domains.setter
    def domains(self, val: set[str]) -> None:
        self._domains = val

    @property
    def ips(self) -> set[str]:
        return self._ips

    @ips.setter
    def ips(self, val: set[str]) -> None:
        self._ips = val

    ## abstract methods

    def _enter(self) -> Node:
        """
        Adds this Node to the network's NodeSet.

        :return: The identity of this Node.
        :rtype: str
        """
        if self.identity in self.network.nodes:
            self.network.nodes[self.identity] = self.merge(self.network.nodes[self.identity])
        else:
            self.network.nodes[self.identity] = self

        self.resolveDNS()

        return self

    def to_psml(self) -> BeautifulSoup:
        soup = super().to_psml()

        body = soup.find('section', id = 'body')
        for section in self.psmlBody:
            body.append(section.tag)
        body.unwrap()

        domains = PropertiesFragment('domains', properties = [
            Property(
                name = 'domain',
                title = 'Domain',
                value = XRef(docid = f'_nd_domain_{domain.replace(".","_")}') \
                    if domain in self.network.domains else domain
            )
            for domain in self.domains
        ])

        ips = PropertiesFragment('ips', properties = [
            Property(
                name = 'ipv4',
                title = 'Public IP' if iptools.public_ip(ip) else 'Private IP',
                value = XRef(docid = f'_nd_ipv4_{ip.replace(".","_")}') \
                    if ip in self.network.ips else ip
            )
            for ip in self.ips
        ])

        header = soup.find('section', id = 'header')
        header.append(domains.tag)
        header.append(ips.tag)

        return soup

    @classmethod
    def from_psml(cls, network: Network, psml: BeautifulSoup, subclass_types: Iterable[Type[Node]] = ()) -> Node:
        ... #TODO implement

    def merge(self, node: Node) -> Node: # type: ignore
        super().merge(node)
        self.domains |= node.domains
        self.ips |= node.ips
        return self

    ## properties

    @property
    def location(self) -> str:
        """
        Returns a location code based on the IPs associated with this node, and the configuration in ``locations.json``.

        :return: The location of this node
        :rtype: str
        """
        return self._location or self.network.locator.locate(self.ips) or '—'

    @location.setter
    def location(self, value: str) -> None:
        self._location = value

    @location.deleter
    def location(self) -> None:
        self._location = None

    ## methods

    def resolveDNS(self) -> None:
        """
        Walks backwards through the DNS for each of this nodes domains / ips,
        setting the node attribute to this object.
        Also adds those dns objects to the internal domain / ip sets.
        """
        cache: set[str] = set()
        for domain in list(self.domains):
            cache |= self._walkBackrefs(
                self.network.find_dns(domain), cache)

        for ip in list(self.ips):
            cache |= self._walkBackrefs(
                self.network.find_dns(ip), cache)

    def _walkBackrefs(self, dnsobj: dns.DNSObject, cache: set[str] = None) -> set[str]:
        """
        Walks through the backrefs of *dnsobj*, 
        setting the node attribute to this object and storing the addresses.

        :param dnsobj: The DNSObject to start with.
        :type dnsobj: Union[str, dns.DNSObject]
        :param cache: [description], defaults to None
        :type cache: set[str], optional
        :return: [description]
        :rtype: set[str]
        """ 
        if not cache:
            cache = set()
        elif dnsobj.name in cache:
            return cache
        cache.add(dnsobj.name)

        if dnsobj.node: 
            if dnsobj.node.type == PlaceholderNode.type:
                logger.debug(
                    f'{self.name} consuming placeholder node from {dnsobj.name}')
                dnsobj.node.merge(self)
                return cache

            elif isinstance(dnsobj.node, ProxiedNode):
                assert dnsobj.node.proxy.node is not None, \
                    'DEBUG: NodeProxy did not create placeholder node.'
                if dnsobj.node.proxy.node.type == PlaceholderNode.type:
                    logger.debug(
                        f'Proxy from {dnsobj.name} to {dnsobj.node.proxy.backend.name}'
                        + f' set to {self.name}')
                    dnsobj.node.proxy.node = self
                
            
            else:
                return cache
        else:
            dnsobj.node = self

        if isinstance(dnsobj, dns.Domain):
            self.domains.add(dnsobj.name)
        else:
            self.ips.add(dnsobj.name)
        
        for backref in dnsobj.implied_links.destinations:
            cache |= self._walkBackrefs(backref, cache)

        return cache


class ProxiedNode(Node):
    """
    Represents a Node behind a proxy, possibly in another network.

    Like a Node, but does not set the node attribute 
    on its registered DNS objects when entering the network.
    """
    proxy: NodeProxy
    """The NodeProxy that sits in front of this Node."""
    type = 'proxied_node'

    def __init__(self,
            network: Network, 
            name: str, 
            identity: str, 
            domains: Iterable[str], 
            ips: Iterable[str],
            labels: Iterable[str] = None,
            proxy_node: Node = None
        ) -> None:
            super().__init__(network, name, identity, domains, ips, labels)
            self.proxy = NodeProxy(self, proxy_node, 
                {addr for addrset in (domains, ips) for addr in addrset})

    def _walkBackrefs(self, dnsobj: dns.DNSObject, cache: set[str] = None) -> set[str]:
        if not cache:
            cache = set()
        elif dnsobj.name in cache:
            return cache
        cache.add(dnsobj.name)

        if dnsobj.node:
            assert not isinstance(dnsobj.node, NodeProxy), \
                f'Conflicting NodeProxies on {dnsobj.name}'

            if self.proxy.node and dnsobj.node is self.proxy.node:
                dnsobj.node = self.proxy # type: ignore

            elif self.proxy.node.type == PlaceholderNode.type:
                logger.debug(
                    f'Proxy from {dnsobj.name} to {self.name}'
                    + f' set to {dnsobj.node.name}')
                self.proxy.node = dnsobj.node
                dnsobj.node = self.proxy # type: ignore

            else:
                logger.debug( #TODO remove warning once properly tested
                    'False address claim from ProxiedNode '+
                    f'{self.identity} on {dnsobj.name}')
        else:
            dnsobj.node = self.proxy # type: ignore
        
        for backref in dnsobj.implied_links.destinations:
            cache |= self._walkBackrefs(backref, cache)

        return cache


class NodeProxy:
    # TODO add tests for this
    """Represents a Node which behaves as a proxy, 
    forwarding some of its traffic to a backend Node."""
    backend: Node
    """The Node the proxy forwards its traffic to."""
    node: Node
    """The Node behaving as the proxy."""
    addresses: set[str]
    """Dict mapping string addresses / paths to Node objects."""
    type = 'proxy'

    def __init__(self, 
            backend: ProxiedNode, 
            proxy: Node = None, 
            addresses: set[str] = None
        ) -> None:
        """
        Constructor.

        :param backend: The Node that this proxy conditionally forwards traffic to.
        :type backend: ProxiedNode
        :param proxy: The Node that performs the forwarding of, defaults to None
        :type proxy: Node, optional
        :param addresses: A set of DNS names that should resolve to the backend, 
        defaults to None
        :type addresses: Node, optional
        """
        self.backend = backend
        self.node = proxy or PlaceholderNode(backend.network, backend.name + '_proxy')
        self.addresses = addresses or set()
    
    def register_address(self, address: str) -> None:
        """
        Registers an address as one which resolves to the backend Node.

        :param address: FQDN + optional path
        :type address: str
        """
        self.addresses.add(address)

    def lookup(self, address: str) -> Optional[Node]:
        """
        Return the backend Node if *address* is registered, 
        otherwise returns the proxy.
        """
        if address in self.addresses:
            return self.backend
        return self.node


class DefaultNode(Node):
    """
    Default implementation of Node, with one private IPv4 address.
    """
    private_ip: str
    """The IP that this Node is using."""
    type = 'default'

    ## dunder methods

    def __init__(self, 
            network: Network,
            name: str, 
            private_ip: str,
            public_ips: Iterable[str] = [],
            domains: Iterable[str] = [],
            labels: Iterable[str] = None
        ) -> None:

        if iptools.valid_ip(private_ip) and not iptools.public_ip(private_ip):
            self.private_ip = private_ip
        else:
            raise ValueError(f'Invalid private IP: {private_ip}')

        super().__init__(
            network = network, 
            name = name,
            identity = private_ip,
            domains = domains,
            ips = [*public_ips] + [private_ip],
            labels = labels
        )


class PlaceholderNode(Node):
    """
    A placeholder Node intended to be consumed by another Node.
    If one of it's domains / ips get the node attribute set, 
    this object will be consumed by the new node and replaced in all locations.
    """
    type = 'placeholder'

    def __init__(self, 
            network: Network, 
            name: str, 
            domains: Iterable[str] = [], 
            ips: Iterable[str] = [],
            labels: Iterable[str] = None
        ) -> None:
        """
        Generates a random UUID to use for it's identity.
        If any of its domains / ips already have a node,
        it will create a ref from its own identity to that node, forcing a merge.
        If there are multiple unique nodes referenced by its DNSObjs, 
        an exception wil be raised.

        :param network: The network.
        :type network: Network
        :param name: Name for this node.
        :type name: str
        :param domains: A set of domains this node will listen on, defaults to []
        :type domains: Iterable[str], optional
        :param ips: A set of ips this node will listen on, defaults to []
        :type ips: Iterable[str], optional
        """

        hash = sha256(usedforsecurity = False)
        hash.update(bytes(name, 'utf-8'))
        hash.update(bytes(str(sorted(set(domains))), 'utf-8'))
        hash.update(bytes(str(sorted(set(ips))), 'utf-8'))

        super().__init__(
            network = network, 
            name = name, 
            identity = hash.hexdigest(), 
            domains = domains, 
            ips = ips,
            labels = labels
        )

        nodes: set[Node] = set()
        for domain in self.domains:
            node = self.network.domains[domain].node
            if node: nodes.add(node)
        for ip in self.ips:
            node = self.network.ips[ip].node
            if node: nodes.add(node)
            
        assert len(nodes) <= 1, 'Placeholder cannot be consumed by more than one node.'
        if nodes:
            self.network.nodes.addRef(nodes.pop(), self.identity)

    ## abstract properties

    @property
    def psmlBody(self) -> list[Tag]:
        """
        Returns an Iterable containing section tags to add to the body of this Node's output PSML.

        :return: A set of ``<section />`` BeautifulSoup tags.
        :rtype: Iterable[Tag]
        """
        return []

    ## properties

    @property
    def aliases(self) -> set[str]:
        """
        Returns all the refs to this node in the containing NodeSet.
        This is useful for guaranteeing this objects removal after consumption.

        :return: A set of refs to this node.
        :rtype: set[str]
        """
        return {ref for ref, node in self.network.nodes.nodes.items() if node is self}

    ## methods

    def _enter(self) -> Node:
        super()._enter()
        return self.network.nodes[self.identity]

    def merge(self, node: Node) -> Node: # type: ignore
        """
        Copies any data in this object to the corresponding attributes in *node*.
        Replaces *self* in all locations with *node*.

        :param node: The Node to merge replace *self* with.
        :type node: Node
        :return: The *node* argument.
        :rtype: Node
        """
        node.domains |= self.domains
        node.ips |= self.ips
        node.psmlFooter.extend(self.psmlFooter)

        for domain in self.domains:
            if self.network.domains[domain].node is self:
                self.network.domains[domain].node = node

        for ip in self.ips:
            if self.network.ips[ip].node is self:
                self.network.ips[ip].node = node

        for alias in self.aliases:
            self.network.nodes[alias] = node

        return node

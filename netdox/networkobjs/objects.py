from __future__ import annotations

import os
import re
from ipaddress import IPv4Address as BaseIP
from typing import TYPE_CHECKING, Iterable, Tuple, Type, Union
from bs4 import BeautifulSoup

import iptools
import utils
from bs4 import Tag

from .base import DNSObject, NetworkObject, RecordSet

if TYPE_CHECKING:
    from . import Network
    from .containers import *

class Domain(DNSObject):
    """
    A domain defined in a managed DNS zone.
    Contains all A/CNAME DNS records from managed zones using this domain as the record name.

    Subclasses DNSObject
    """
    _node: Node
    
    ## dunder methods

    def __init__(self, name: str, zone: str = None, role: str = 'default') -> None:
        """
        Initialises a Domain

        :param name: The domain name to use
        :type name: str
        :param zone: The parent DNS zone, defaults to None
        :type zone: str, optional
        :param role: The DNS role to apply to this domain, defaults to 'default'
        :type role: str, optional
        :raises ValueError: If *name* is not a valid FQDN
        """
        if re.fullmatch(utils.dns_name_pattern, name):
            self.name = name.lower()
            self.zone = zone.lower() if zone else None
            self.role = role.lower()

            self.docid = f'_nd_domain_{self.name.replace(".","_")}'
            self.location = None
            self.subnets = set()
            self._node = None
            self.psmlFooter = []
            
            self.records = {
                'A': RecordSet(),
                'CNAME': RecordSet()
            }

            self.backrefs = {
                'CNAME': set(),
                'PTR': set()
            }
        else:
            raise ValueError('Must provide a valid name for dns record (some FQDN)')
    
    ## abstract properties

    @property
    def network(self) -> Network:
        """
        Return the current _network attribute

        :return: The current Network
        :rtype: Network
        """
        return self._network

    @network.setter
    def network(self, new_network: Network) -> None:
        """
        Set the _network attribute to new_network.
        Also updates the location and creates implied links from any IPv4Addresses this Domain resolves to, back to itself.

        :param new_network: The network this Domain has been added to.
        :type new_network: Network
        """
        self._network = new_network
        self.location = new_network.locator.locate(self.ips)
        for ip in self.ips:
            if ip not in self.network:
                self.network.add(IPv4Address(ip))
            self.network.ips[ip].implied_ptr.add(self.name)

    @property
    def outpath(self) -> str:
        return os.path.abspath(f'out/domains/{self.docid}.psml')
    
    ## abstract methods

    def link(self, destination: str, source: str) -> None:
        """
        Adds a DNS record from this domain to the provided destination.

        Adds a 2-tuple containing the destination and source to the relevant record set; self._cnames when destination is a FQDN, etc.

        :param destination: The value for the DNS record, as a string.
        :type destination: str
        :param source: The plugin that provided this link.
        :type source: str
        :raises ValueError: If the destination cannot be recognised as a FQDN or IPv4 address.
        """
        if iptools.valid_ip(destination):
            self.records['A'].add(destination, source)
            if not iptools.public_ip(destination):
                self.subnets.add(iptools.sort(destination))
        elif re.fullmatch(utils.dns_name_pattern, destination):
            self.records['CNAME'].add(destination, source)
        else:
            raise ValueError('Unable to parse value as a domain or IPv4 address')

    def merge(self, domain: Domain) -> Domain:
        """
        In place merge of two Domain instances.
        This method should always be called on the object entering the set.

        :param domain: The Domain to merge with.
        :type domain: Domain
        :raises ValueError: If the Domain objects cannot be merged (if their name attributes are not equal).
        :return: This Domain object, which is now a superset of the two.
        :rtype: Domain
        """
        if self.name == domain.name:
            self.psmlFooter += domain.psmlFooter
            self.subnets |= domain.subnets

            for type in self.records:
                for dest, source in domain.records[type]._records:
                    self.link(dest, source)

            for type in self.backrefs:
                for dest in domain.backrefs[type]:
                    self.backrefs[type].add(dest)

            if domain.network:
                self._network = domain.network

            return self
        else:
            raise ValueError('Cannot merge two Domains with different names')

    def to_dict(self) -> dict:
        return super().to_dict() | {'_node': None, '_container': None}

    ## properties

    @property
    def container(self) -> DomainSet:
        """
        Returns the current _container attribute

        :return: The current DomainSet this Domain is in.
        :rtype: Domain
        """
        return self._container

    @container.setter
    def container(self, new_container: Domain) -> None:
        """
        Set the _container attribute to new_container.
        Also updates the role attribute.

        :param new_network: The network this Domain has been added to.
        :type new_network: Network
        """
        self._container = new_container
        for role, domains in self.container.roles.items():
            if self.name in domains:
                self.role = role

    @property
    def node(self) -> Node:
        """
        Returns the Node this Domain resolves to.

        :return: The Node this Domain resolves to, or None.
        :rtype: Node
        """
        return self._node

    @node.setter
    def node(self, new_node: Node) -> None:
        self._node = new_node
        if new_node.location:
            self.location = new_node.location

class IPv4Address(DNSObject, BaseIP):
    """
    A single IP address found in the network
    """
    nat: RecordSet
    """The IP this address resolves to through the NAT."""
    unused: bool
    """Whether or not a Domain in the network resolves to this IP."""
    
    ## dunder methods

    def __init__(self, address: object, unused: bool = False) -> None:
        super().__init__(address)
        self.name = self.name
        self.location = None
        self.unused = unused
        
        self.docid = f'_nd_ip_{self.name.replace(".","_")}'
        self.subnets = set([iptools.sort(self.name)])
        self.nat = None
        self.node = None

        self.records = {
            'PTR': RecordSet(),
            'CNAME': RecordSet()
        }

        self.backrefs = {
            'A': RecordSet(),
            'CNAME': RecordSet()
        }
    
    ## abstract properties

    @property
    def network(self) -> Network:
        """
        Return the current _network attribute

        :return: The current Network
        :rtype: Network
        """
        return self._network

    @network.setter
    def network(self, new_network: Network) -> None:
        """
        Set the _network attribute to new_network.
        Also updates the location and creates implied links from any Domains this IPv4Address resolves to, back to itself.

        :param new_network: The network this IPv4Address has been added to.
        :type new_network: Network
        """
        self._network = new_network
        self.location = new_network.locator.locate([self.name])
        for domain in self.domains:
            if domain in self.network:
                self.network.domains[domain].implied_ips.add(self.name)

    @property
    def outpath(self) -> str:
        return os.path.abspath(f'out/ips/{self.subnet.replace("/","_")}/{self.docid}.psml')
    
    ## abstract methods

    def link(self, value: str, source: str) -> None:
        """
        Adds a record from this object to a DNSObject named *value*.

        :param value: The name of the DNSObject to link to.
        :type value: str
        :param source: The plugin that provided this link.
        :type source: str
        """
        if iptools.valid_ip(value):
            self.records['CNAME'].add(value, source)
        elif re.fullmatch(utils.dns_name_pattern, value):
            self.records['PTR'].add(value, source)
        else:
            raise ValueError('Unable to parse value as a domain or IPv4 address')

    def merge(self, ip: IPv4Address) -> IPv4Address:
        """
        In place merge of two IPv4Address instances.
        This method should always be called on the object entering the set.

        :param ip: The IPv4Address to merge with.
        :type ip: IPv4Address
        :raises ValueError: If the IPv4Address objects cannot be merged (if their addr attributes are not equal).
        :return: This IPv4Address object, which is now a superset of the two.
        :rtype: IPv4Address
        """
        if self.name == ip.name:
            self.psmlFooter += ip.psmlFooter
            self.nat = ip.nat or self.nat

            for type in self.records:
                for dest, source in ip.records[type]._records:
                    self.link(dest, source)

            for type in self.backrefs:
                for dest in ip.backrefs[type]:
                    self.backrefs[type].add(dest)

            if ip.network:
                self.network = ip.network
                
            return self
        else:
            raise ValueError('Cannot merge two IPv4Addresses with different addresses')

    def to_dict(self) -> dict:
        return super().to_dict() | {'node': None}
    
    ## properties

    @property
    def subnet(self) -> str:
        return self.subnets[0]


class Node(NetworkObject):
    """
    A Node on the network representing one machine/VM/Kubelet/etc.
    Name should be the FQDN of the machine unless it has a non-default type.
    """
    private_ip: str
    """The IP that this Node is using."""
    public_ips: set
    """A set of public IPs that this Node uses."""
    domains: set
    """A set of domains that are hosted on this Node."""
    type: str
    """The type of this Node."""

    def __init__(self, 
            name: str, 
            private_ip: str, 
            public_ips: Iterable[str] = None, 
            domains: Iterable[str] = None, 
            type: str = 'default'
        ) -> None:

        self.name = name.strip().lower()
        self.docid = f'_nd_node_{self.name.replace(".","_")}'
        self.type = type
        self.location = None

        if iptools.valid_ip(private_ip) and not iptools.public_ip(private_ip):
            self.private_ip = private_ip
        else:
            raise ValueError(f'Invalid private IP: {private_ip}')
            
        self.public_ips = set(public_ips) if public_ips else set()
        self.domains = set(domains) if domains else set()

        self.psmlFooter = []

    @property
    def ips(self) -> list[str]:
        """
        Return all the IPs that resolve to this node.

        :return: A list of IPv4 addresses as strings.
        :rtype: list[str]
        """
        return list(self.public_ips) + [self.private_ip]

    @property
    def network(self) -> Network:
        """
        Return the current _network attribute

        :return: The current Network
        :rtype: Network
        """
        return self._network

    @network.setter
    def network(self, new_network: Network) -> None:
        """
        Set the _network attribute to new_network.
        Also updates the location and sets the *node* attribute of any Domains or IPv4Addresses that resolve to this node.

        :param new_network: The network this IPv4Address has been added to.
        :type new_network: Network
        """
        self._network = new_network
        self.location = new_network.locator.locate(self.ips)

        for domain in self.domains:
            if domain in self.network:
                self.network.domains[domain].node = self

        for ip in self.ips:
            if ip not in self.network:
                self.network.add(IPv4Address(ip))
            self.network.ips[ip].node = self

    @property
    def outpath(self) -> str:
        return os.path.abspath(f'out/nodes/{self.docid}.psml')

    @property
    def psmlBody(self) -> Iterable[Tag]:
        """
        Returns an Iterable containing section tags to add to the body of this Node's output PSML.

        :return: A set of ``<section />`` BeautifulSoup tags.
        :rtype: Iterable[Tag]
        """
        return []

    def merge(self, node: Node) -> Node:
        """
        In place merge of two Node instances.
        This method should always be called on the object entering the set.

        :param node: The Node to merge with.
        :type node: Node
        :raises TypeError: If the node to merge with is not of 'default' type or has a different private_ip attribute.
        :return: This Node object, which is now a superset of the two.
        :rtype: Node
        """
        if self.type == node.type and self.private_ip == node.private_ip:
            self.psmlFooter += node.psmlFooter
            self.public_ips |= node.public_ips
            self.domains |= node.domains
            if node.network:
                self.network = node.network
            return self
        else:
            raise TypeError('Cannot merge two Nodes of different types or different private ips')

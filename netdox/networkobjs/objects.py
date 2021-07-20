from __future__ import annotations

import re
from ipaddress import IPv4Address as BaseIP
from typing import TYPE_CHECKING, Iterable, Tuple, Type, Union

import iptools
import utils
from bs4 import Tag

from .base import NetworkObject

if TYPE_CHECKING:
    from . import Network
    from .containers import *


class Domain(NetworkObject):
    """
    A domain defined in a managed DNS server.
    Contains all A/CNAME DNS records from managed servers using this domain as the record name.

    Subclasses NetworkObject
    """
    root: str
    """The root DNS zone this domain was found in."""
    role: str
    """The configured DNS role this domain has been assigned."""
    node: Node
    """The Node this domain is hosted on."""
    _container: DomainSet
    _public_ips: set[str]
    _private_ips: set[str]
    _cnames: set[str]
    implied_ips: set[str]
    """A set of IPv4Addresses as strings have a PTR record resolving to this domain."""
    subnets: set[str]
    """The /24 subnets this domains private ips are in."""

    def __init__(self, name: str, root: str = None, role: str = 'default') -> None:
        """
        Initialises a Domain

        :param name: The domain name to use
        :type name: str
        :param root: The root DNS zone, defaults to None
        :type root: str, optional
        :param role: The DNS role to apply to this domain, defaults to 'default'
        :type role: str, optional
        :raises ValueError: If *name* is not a valid FQDN
        """
        if re.fullmatch(utils.dns_name_pattern, name):
            self.name = name.lower()
            self.docid = f'_nd_domain_{self.name.replace(".","_")}'
            self.root = root.lower() if root else None
            self.role = role.lower()
            self.location = None

            # destinations
            self._public_ips = set()
            self._private_ips = set()
            self._cnames = set()

            self.implied_ips = set()
            self.subnets = set()

            self.node = None
            self.psmlFooter = []
        else:
            raise ValueError('Must provide a valid name for dns record (some FQDN)')

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
        destination = destination.lower().strip()
        if iptools.valid_ip(destination):
            recordtype = 'A'
        elif re.fullmatch(utils.dns_name_pattern, destination):
            recordtype = 'CNAME'
        else:
            raise ValueError('Unable to parse destination as a domain or IPv4 address')
                
        if recordtype == 'A':
            if iptools.public_ip(destination):
                self._public_ips.add((destination, source))
            else:
                self._private_ips.add((destination, source))
        else:
            self._cnames.add((destination, source))
        
        self.update()

    def update(self) -> None:
        """
        Updates subnet and location data for this record.
        """
        for ip in self.private_ips:
            self.subnets.add(iptools.sort(ip))
        if self.network:
            self.location = self.network.locator.locate(self.ips)

    @property
    def destinations(self) -> list[str]:
        """
        Returns a list of all the domains and IPv4 addresses this Domain resolves to, as strings.

        :return: A list of FQDNs and IPv4 addresses, as strings.
        :rtype: list
        """
        return self.public_ips + self.private_ips + self.cnames

    @property
    def _ips(self) -> set[Tuple[str, str]]:
        """
        Returns a set of the 2-tuples representing DNS records from self._public_ips and self._private_ips combined.

        :return: A set of 2-tuples containing an IPv4 address and the plugin the link came from.
        :rtype: set[Tuple[str, str]]
        """
        return self._public_ips.union(self._private_ips)

    @property
    def public_ips(self) -> list[str]:
        """
        Returns all IPs from this domain's links that are outside of protected ranges.

        :return: A list of IPv4 addresses as strings.
        :rtype: list[str]
        """
        return list(set([ip for ip,_ in self._public_ips]))

    @property
    def private_ips(self) -> list[str]:
        """
        Returns all IPs from this domain's links that are inside a protected range.

        :return: A list of IPv4 addresses as strings.
        :rtype: list[str]
        """
        return list(set([ip for ip,_ in self._private_ips]))

    @property
    def ips(self) -> list[str]:
        """
        Returns all IPs from this domain's links.

        :return: A list of IPv4 addresses as strings.
        :rtype: list[str]
        """
        return [ip for ip, _ in self._ips]

    @property
    def iplinks(self) -> list[str]:
        """
        Returns all ips that this domain points to, or that point back

        :return: A list of IPv4 addresses as strings.
        :rtype: list[str]
        """
        return list(set(self.ips) + self.implied_ips)

    @property
    def cnames(self) -> list[str]:
        """
        Returns all ips that this domain points to, or that point back

        :return: A list of FQDNs.
        :rtype: list[str]
        """
        return list(set([cname for cname,_ in self._cnames]))

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
            self._private_ips |= domain._private_ips
            self._public_ips |= domain._public_ips
            self._cnames |= domain._cnames
            if domain.network:
                self._network = domain.network
            self.update()
            return self
        else:
            raise ValueError('Cannot merge two Domains with different names')

    def to_dict(self) -> dict:
        return super().to_dict() | {'node': None, '_container': None}

    @classmethod
    def from_dict(cls: Type[Domain], string: str) -> Domain:
        """
        Instantiates a Domain from its __dict__ attribute.

        :param constructor: The dictionary to use.
        :type constructor: dict
        :return: A instance of this class.
        :rtype: Domain
        """
        instance = super(Domain, cls).from_dict(string)
        instance.implied_ips = set(instance.implied_ips)
        for attribute in ('_public_ips', '_private_ips', '_cnames'):
            listAttr = getattr(instance, attribute)
            setattr(instance, attribute, {(value, plugin) for value, plugin in listAttr})
        return instance


class IPv4Address(BaseIP, NetworkObject):
    """
    A single IP address found in the network
    """
    addr: str
    """Same as name. This IP as a string."""
    node: Node
    """The Node using this IP."""
    subnet: str
    """The /24 subnet this IP is in."""
    _ptr: set[Tuple[str, str]]
    implied_ptr: set[str]
    """A set of domains which resolve to this IP."""
    nat: str
    """The IP this address resolves to through the NAT."""
    unused: bool
    """Whether or not a Domain in the network resolves to this IP."""

    def __init__(self, address: object, unused: bool = False) -> None:
        super().__init__(address)
        self.addr = str(address)
        self.name = self.addr
        self.docid = f'_nd_ip_{self.addr.replace(".","_")}'
        self.subnet = iptools.sort(self.addr)
        self.location = None
        self.unused = unused
        
        self._ptr = set()
        self.implied_ptr = set()
        self.nat = None
        self.node = None
        self.psmlFooter = []

    def link(self, domain: str, source: str):
        """
        Adds a PTR record from this IP to the provided domain.

        Adds a 2-tuple containing the domain and source to self._ptr

        :param domain: The domain for the PTR record, as a string.
        :type domain: str
        :param source: The plugin that provided this link.
        :type source: str
        :raises ValueError: If the domain cannot be recognised as a valid FQDN.
        """
        if re.fullmatch(utils.dns_name_pattern, domain):
            self._ptr.add((domain, source))
        else:
            raise ValueError(f'Invalid domain \'{domain}\'')

    def subnetFromMask(self, mask: Union[str, int] = '24') -> str:
        """
        Return the subnet of a given size containing this IP

        :param mask: The subnet mask to use in bits, defaults to '24'
        :type mask: Union[str, int], optional
        :return: A IPv4 subnet in CIDR format
        :rtype: str
        """
        mask = str(mask) if isinstance(mask, int) else mask
        subnet = f'{self.addr}/{mask}'
        return f'{iptools.subn_floor(subnet)}/{mask}'

    @property
    def ptr(self) -> list[str]:
        """
        Returns all domains from this IPs links

        :return: A list of FQDNs
        :rtype: list[str]
        """
        return [domain for domain, _ in self._ptr]

    @property
    def domains(self) -> set[str]:
        """
        Returns the superset of domains this IP points to, and domains which point back.

        :return: A set of FQDNs
        :rtype: set[str]
        """
        return set(self.ptr).union(self.implied_ptr)

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
        self.location = new_network.locator.locate([self.addr])
        for domain in self.domains:
            if domain in self.network:
                self.network.domains[domain].implied_ips.add(self.addr)

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
        if self.addr == ip.addr:
            self._ptr |= ip._ptr
            self.implied_ptr |= ip.implied_ptr
            self.nat = ip.nat or self.nat
            if ip.network:
                self.network = ip.network
            return self
        else:
            raise ValueError('Cannot merge two IPv4Addresses with different addresses')

    def to_dict(self) -> dict:
        return super().to_dict() | {'node': None}

    @classmethod
    def from_dict(cls: Type[IPv4Address], string: str) -> IPv4Address:
        """
        Instantiates an IPv4Address from its __dict__ attribute.

        :param constructor: The dictionary to use.
        :type constructor: dict
        :return: A instance of this class.
        :rtype: IPv4Address
        """
        instance = super(IPv4Address, cls).from_dict(string)
        instance.implied_ptr = set(instance.implied_ptr)
        instance._ptr = {(domain, plugin) for domain, plugin in instance._ptr}
        return instance


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
        :rtype: [type]
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
            self.public_ips |= node.public_ips
            self.domains |= node.domains
            if node.network:
                self.network = node.network
            return self
        else:
            raise TypeError('Cannot merge two Nodes of different types or different private ips')

    @classmethod
    def from_dict(cls: Type[Node], string: str) -> Node:
        """
        Instantiates a Node from its __dict__ attribute.

        :param constructor: The dictionary to use.
        :type constructor: dict
        :return: A instance of this class.
        :rtype: Node
        """
        instance = super(Node, cls).from_dict(string)
        instance.public_ips = set(instance.public_ips)
        instance.domains = set(instance.domains)
        return instance

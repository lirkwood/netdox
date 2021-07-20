from __future__ import annotations

import re
from ipaddress import IPv4Address as BaseIP
from typing import TYPE_CHECKING, Iterator, Tuple, Type, Union

import iptools

from utils import dns_name_pattern

from .base import NetworkObject, NetworkObjectContainer

if TYPE_CHECKING:
    from . import Network
    from .base import NetworkObject, NetworkObjectContainer
    from .domains import Domain
    from .nodes import Node

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

    def link(self, domain: Union[Domain, str], source: str):
        """
        Adds a PTR record from this IP to the provided domain.

        Adds a 2-tuple containing the domain and source to self._ptr

        :param domain: The domain for the PTR record.
        :type domain: Union[Domain, str]
        :param source: The plugin that provided this link.
        :type source: str
        :raises ValueError: If the domain cannot be recognised as a valid FQDN.
        """
        if isinstance(domain, Domain):
            self._ptr.add((domain.name, source))
        elif re.fullmatch(dns_name_pattern, domain):
            self._ptr.add((domain, source))
        else:
            raise ValueError(f'Invalid domain \'{domain.name if isinstance(domain, Domain) else domain}\'')

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


class IPv4AddressSet(NetworkObjectContainer):
    """
    Container for a set of IPv4Address
    """
    objectType: str = 'ips'
    objectClass: Type[IPv4Address] = IPv4Address
    subnets: set
    """A set of the /24 subnets of the private IPs in this container."""

    def __init__(self, ips: list[IPv4Address] = [], network: Network = None) -> None:
        super().__init__(ips, network)
        self.subnets = set()

    def __getitem__(self, key: str) -> IPv4Address:
        return self.objects[key]

    def __iter__(self) -> Iterator[IPv4Address]:
        yield from super().__iter__()

    def add(self, ip: IPv4Address) -> None:
        """
        Add a single IPv4Address to the set, merge if that IP is already in the set. 
        Add the /24 bit subnet to the set of subnets.

        :param ip: The IPv4Address to add to the set
        :type ip: IPv4Address
        """
        super().add(ip)
        if ip.is_private:
            self.subnets.add(ip.subnetFromMask())

    @property
    def ips(self) -> dict[str, IPv4Address]:
        """
        Returns the underlying objects dict.

        :return: A dictionary of the IPv4Addresses in this set, with addresses as keys.
        :rtype: dict
        """
        return self.objects

    @property
    def private_ips(self) -> list[IPv4Address]:
        """
        Returns all IPs in the set that are part of the private namespace

        :return: A list of IPv4Address objects
        :rtype: list[IPv4Address]
        """
        return [ip for ip in self if ip.is_private]

    @property
    def public_ips(self) -> list[IPv4Address]:
        """
        Returns all IPs in the set that are not part of the private namespace

        :return: A list of IPv4Address objects
        :rtype: list[IPv4Address]
        """
        return [ip for ip in self if not ip.is_private]

    @property
    def unused(self) -> list[IPv4Address]:
        """
        Returns all IPs in the set that are not referenced by a DNS record.

        :return: A list of IPv4Address objects
        :rtype: list[IPv4Address]
        """
        return [ip for ip in self if ip.unused]

    @property
    def used(self) -> list[IPv4Address]:
        """
        Returns all IPs in the set that are referenced by a DNS record.

        :return: A list of IPv4Address objects
        :rtype: list[IPv4Address]
        """
        return [ip for ip in self if not ip.unused]

    def fillSubnets(self) -> None:
        """
        Iterates over each unique private subnet this set has IP addresses in, 
        and generates IPv4Addresses for each IP in the subnet not already in the set (with the unused attribute set).
        If the set has a Network, any IPs referenced by a domain/node not already present will be generated as well.
        """
        for subnet in self.subnets:
            for ip in iptools.subn_iter(subnet):
                if ip not in self:
                    self[ip] = IPv4Address(ip, True)
        
        if self.network:
            for domain in self.network.domains:
                for ip in domain.ips:
                    if ip not in self:
                        self.add(IPv4Address(ip))
            for node in self.network.nodes:
                for ip in node.ips:
                    if ip not in self:
                        self.add(IPv4Address(ip))

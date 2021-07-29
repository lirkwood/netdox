from __future__ import annotations

from typing import TYPE_CHECKING, Iterator, Type

import iptools
from utils import DEFAULT_ROLES

from .base import NetworkObjectContainer
from .objects import Domain, IPv4Address, Node

if TYPE_CHECKING:
    from . import Network


class DomainSet(NetworkObjectContainer):
    """
    Container for a set of Domains
    """
    objectType: str = 'domains'
    objectClass: Type[Domain] = Domain
    _roles: dict

    def __init__(self, objectSet: list[Domain] = [], network: Network = None, roles: dict = None) -> None:
        super().__init__(objectSet, network)
        self._roles = roles or DEFAULT_ROLES

    def __getitem__(self, key: str) -> Domain:
        return self.objects[key]

    ## Re-implemented to type hint
    def __iter__(self) -> Iterator[Domain]:
        yield from super().__iter__()

    @property
    def domains(self) -> dict[str, Domain]:
        """
        Returns the underlying objects dict.

        :return: A dictionary of the Domains in this set, with names as keys.
        :rtype: dict
        """
        return self.objects
    
    @property
    def roles(self) -> dict[str, list[str]]:
        """
        Returns dictionary of roles and their domains (except the *exclusions* role)

        :return: A dictionary of lists of FQDNs
        :rtype: dict
        """
        return {k: v['domains'] for k, v in self._roles.items() if k != 'exclusions'}

    @roles.setter
    def roles(self, value: dict) -> None:
        """
        Sets the _roles attribute

        :param value: The new value for the _role attribute
        :type value: dict
        """
        self._roles = value

    @roles.deleter
    def roles(self) -> None:
        """
        Deletes the _roles attribute
        """
        del self._roles

    @property
    def exclusions(self) -> list[str]:
        """
        Returns a list of excluded domains

        :return: A list of FQDNs
        :rtype: list[str]
        """
        return self._roles['exclusions']

    def add(self, domain: Domain) -> None:
        """
        Add a single domain to the set if it is not in the exclusions list.
        Merge if an object with that name is already present.

        :param domain: The Domain to add to the set.
        :type domain: Domain
        """
        if domain.name not in self.exclusions:
            super().add(domain)


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


class NodeSet(NetworkObjectContainer):
    """
    Container for a set of Nodes
    """
    objectType: str = 'nodes'
    objectClass: Type[Node] = Node

    def __init__(self, objectSet: list[Node] = [], network: Network = None) -> None:
        self.objects = {object.docid: object for object in objectSet}
        self.network = network

    def __iter__(self) -> Iterator[Node]:
        yield from super().__iter__()

    def __getitem__(self, key: str) -> Node:
        return self.objects[key]

    @property
    def nodes(self) -> dict[str, Node]:
        """
        Returns the underlying objects dict

        :return: A dictionary of the Nodes in the set, with docids as keys
        :rtype: dict[str, Node]
        """
        return self.objects

    def add(self, node: Node) -> None:
        """
        Add a single Node to the set, merge if a Node with that docid is already present.

        :param object: The Node to add to the set.
        :type object: Node
        """
        if node.docid in self:
            self[node.docid] = node.merge(self[node.docid])
        else:
            if self.network:
                node.network = self.network
            self[node.docid] = node

    def replace(self, identifier: str, replacement: Node) -> None:
        """
        Replace the Node with the specified identifier with a new Node.

        Calls merge on the replacement with the target Node passed as the argument,
        then mutates the original Node into the superset, preserving its identity.
        Also adds a ref under the replacement's docid in ``self.objects``.

        If target Node is not in the set, the new Node is simply added as-is, 
        and *identifier* will point to it.

        :param identifier: The string to use to identify the existing object to replace.
        :type identifier: str
        :param object: The Node to replace the existing Node with.
        :type object: Node
        """
        if identifier in self:
            original = self[identifier]
            superset = replacement.merge(original)
            original.__class__ = superset.__class__
            for key, val in superset.__dict__.items():
                original.__dict__[key] = val
            self[replacement.docid] = original
        else:
            self.add(replacement)
            self[identifier] = replacement
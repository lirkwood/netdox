from __future__ import annotations

from typing import Iterable, TYPE_CHECKING, Iterator, Type, Union

import iptools
from utils import DEFAULT_DOMAIN_ROLES

from . import base, objects

if TYPE_CHECKING:
    from . import Network


class DomainSet(base.DNSObjectContainer):
    """
    Container for a set of Domains
    """
    objectType: str = 'domains'
    objectClass: Type[objects.Domain] = objects.Domain
    _roles: dict

    def __init__(self, network: Network, domains: Iterable[objects.Domain] = [], roles: dict = None) -> None:
        super().__init__(network, domains)
        self._roles = roles or DEFAULT_DOMAIN_ROLES

    def __getitem__(self, key: str) -> objects.Domain:
        return super().__getitem__(key)

    ## Re-implemented to type hint
    def __iter__(self) -> Iterator[objects.Domain]:
        yield from super().__iter__()

    @property
    def domains(self) -> dict[str, objects.Domain]:
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

    def _add(self, domain: objects.Domain) -> None:
        """
        Add a single domain to the set if it is not in the exclusions list.
        Merge if an object with that name is already present.

        :param domain: The Domain to add to the set.
        :type domain: Domain
        """
        if domain.name not in self.exclusions:
            super()._add(domain)


class IPv4AddressSet(base.DNSObjectContainer):
    """
    Container for a set of IPv4Address
    """
    objectType: str = 'ips'
    objectClass: Type[objects.IPv4Address] = objects.IPv4Address
    subnets: set
    """A set of the /24 subnets of the private IPs in this container."""

    def __init__(self, network: Network, ips: list[objects.IPv4Address] = []) -> None:
        super().__init__(network, ips)
        self.subnets = set()

    def __getitem__(self, key: str) -> objects.IPv4Address:
        return super().__getitem__(key)

    def __iter__(self) -> Iterator[objects.IPv4Address]:
        yield from super().__iter__()

    def _add(self, ip: objects.IPv4Address) -> None:
        """
        Add a single IPv4Address to the set, merge if that IP is already in the set. 
        Add the /24 bit subnet to the set of subnets.

        :param ip: The IPv4Address to add to the set
        :type ip: IPv4Address
        """
        super()._add(ip)
        if ip.is_private:
            self.subnets.add(ip.subnetFromMask())

    @property
    def ips(self) -> dict[str, objects.IPv4Address]:
        """
        Returns the underlying objects dict.

        :return: A dictionary of the IPv4Addresses in this set, with addresses as keys.
        :rtype: dict
        """
        return self.objects

    @property
    def private_ips(self) -> list[objects.IPv4Address]:
        """
        Returns all IPs in the set that are part of the private namespace

        :return: A list of IPv4Address objects
        :rtype: list[IPv4Address]
        """
        return [ip for ip in self if ip.is_private]

    @property
    def public_ips(self) -> list[objects.IPv4Address]:
        """
        Returns all IPs in the set that are not part of the private namespace

        :return: A list of IPv4Address objects
        :rtype: list[IPv4Address]
        """
        return [ip for ip in self if not ip.is_private]

    @property
    def unused(self) -> list[objects.IPv4Address]:
        """
        Returns all IPs in the set that are not referenced by a DNS record.

        :return: A list of IPv4Address objects
        :rtype: list[IPv4Address]
        """
        return [ip for ip in self if ip.unused]

    @property
    def used(self) -> list[objects.IPv4Address]:
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
                    self[ip] = objects.IPv4Address(self.network, ip, True)


class NodeSet(base.NetworkObjectContainer):
    """
    Container for a set of Nodes
    """
    objectType: str = 'nodes'
    objectClass: Type[base.Node] = base.Node

    def __init__(self, network: Network, nodeSet: list[base.Node] = []) -> None:
        self.objects = {node.identity: node for node in nodeSet}
        self.network = network

    def __getitem__(self, key: str) -> base.Node:
        return super().__getitem__(key)

    def __iter__(self) -> Iterator[base.Node]:
        yield from super().__iter__()

    def __contains__(self, key: Union[str, base.Node]) -> bool:
        if isinstance(key, str):
            return super().__contains__(key)
        else:
            return super().__contains__(key.identity)

    @property
    def nodes(self) -> dict[str, base.Node]:
        """
        Returns the underlying objects dict

        :return: A dictionary of the Nodes in the set, with identities as keys
        :rtype: dict[str, Node]
        """
        return self.objects

    def _add(self, node: base.Node) -> None:
        """
        Add a single Node to the set, merge if a Node with that identity is already present.

        :param object: The Node to add to the set.
        :type object: Node
        """
        if node.identity in self:
            self[node.identity] = node.merge(self[node.identity])
        else:
            self[node.identity] = node
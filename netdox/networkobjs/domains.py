from __future__ import annotations

import re
from typing import TYPE_CHECKING, Iterator, Tuple, Type, Union

import iptools

import utils

from .base import NetworkObject, NetworkObjectContainer

if TYPE_CHECKING:
    from . import Network
    from .ips import IPv4Address
    from .nodes import Node

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

    def link(self, destination: Union[Domain, IPv4Address, str], source: str) -> None:
        """
        Adds a DNS record from this domain to the provided destination.

        Adds a 2-tuple containing the destination and source to the relevant record set; self._cnames when destination is a FQDN, etc.

        :param destination: The value for the DNS record.
        :type destination: Union[Domain, IPv4Address, str]
        :param source: The plugin that provided this link.
        :type source: str
        :raises ValueError: If the destination is a string but cannot be recognised as a FQDN or IPv4 address.
        :raises TypeError: If the destination is not one of: Domain, IPv4Address, str
        """
        if isinstance(destination, IPv4Address):
            recordtype = 'A'
            destination = destination.addr
        elif isinstance(destination, Domain):
            recordtype = 'CNAME'
            destination = destination.name
        
        elif isinstance(destination, str):
            destination = destination.lower().strip()
            if iptools.valid_ip(destination):
                recordtype = 'A'
            elif re.fullmatch(utils.dns_name_pattern, destination):
                recordtype = 'CNAME'
            else:
                raise ValueError('Unable to parse destination as a domain or IPv4 address')
        else:
            raise TypeError(f'DNS record destination must be one of: Domain, IPv4Address, str; Not {type(destination)}')
                
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


class DomainSet(NetworkObjectContainer):
    """
    Container for a set of Domains
    """
    objectType: str = 'domains'
    objectClass: Type[Domain] = Domain
    _roles: dict

    def __init__(self, objectSet: list[Domain] = [], network: Network = None, roles: dict = None) -> None:
        super().__init__(objectSet, network)
        self._roles = roles or utils.DEFAULT_ROLES

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

    def applyRoles(self) -> None:
        """
        Sets the role attribute on domains in set where it is configured, 'default' otherwise.
        """
        for role, roleConfig in self._roles.items():
            if role == 'exclusions':
                for domain in roleConfig:
                    if domain in self:
                        del self[domain]
            else:
                for domain in roleConfig['domains']:
                    if domain in self:
                        self[domain].role = role
    
        for domain in self:
            if domain.role is None:
                domain.role = 'default'

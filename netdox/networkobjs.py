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
from abc import ABC, abstractmethod
from datetime import datetime
from ipaddress import IPv4Address as BaseIP
from typing import Iterable, Iterator, Tuple, Union

import iptools
import utils

dns_name_pattern = re.compile(r'([a-zA-Z0-9_-]+\.)+[a-zA-Z0-9_-]+')

##################
# Helper Classes #
##################

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


class JSONEncoder(json.JSONEncoder):
    """
    JSON Encoder compatible with NetworkObjects, sets, and datetime objects
    """
    def default(self, obj):
        """
        :meta private:
        """
        if isinstance(obj, NetworkObject):
            return obj.__dict__ | {'node': obj.node.docid if hasattr(obj, 'node') and obj.node else None}
        elif isinstance(obj, NetworkObjectContainer):
            return None
        elif isinstance(obj, Network):
            return None
        elif isinstance(obj, set):
            return sorted(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return super().default(obj)


###################
# Network Objects #
###################

class NetworkObject(ABC):
    """
    Base class for an object in the network.
    """
    name: str
    docid: str
    _network: Network
    container: NetworkObjectContainer
    location: str

    @property
    def network(self) -> Network:
        """
        Return the current _network attribute

        :return: The current Network
        :rtype: Network
        """
        return self._network

    @network.setter
    @abstractmethod
    def network(self, new_network: Network):
        """
        Set the _network attribute to new_network.
        Should also trigger any link resolution etc. that must be done upon entering a network.

        :param new_network: The network this NetworkObject has been added to.
        :type new_network: Network
        """
        self._network = new_network
        self.location = new_network.locator.locate(self)
    
    @abstractmethod
    def merge(self, object: NetworkObject) -> NetworkObject:
        """
        In place merge of two NetworkObject instances of the same type.
        Must return self.
        This method should always be called on the object entering the set.
        """
        return self


class Domain(NetworkObject):
    """
    A domain defined in a managed DNS server.
    Contains all A/CNAME DNS records from managed servers using this domain as the record name.

    Subclasses NetworkObject
    """
    root: str
    role: str
    node: Node
    _container: DomainSet
    _public_ips: set[str]
    _private_ips: set[str]
    _cnames: set[str]
    implied_ips: set[str]
    subnets: set[str]

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
        if re.fullmatch(dns_name_pattern, name):
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
            elif re.fullmatch(dns_name_pattern, destination):
                recordtype = 'CNAME'
            else:
                raise ValueError('Unable to parse destination as a domain or IPv4 address')
        else:
            raise TypeError(f'DNS record destination must be one of: Domain, IPv4Address, str; Not {type(destination)}')
                
        if recordtype == 'A':
            if iptools.public_ip(destination):
                self._private_ips.add((destination, source))
            else:
                self._public_ips.add((destination, source))
        else:
            self._cnames.add((destination, source))
        
        self.update()

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
        for role, domains in self.container.roles:
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

    def update(self) -> None:
        """
        Updates subnet and location data for this record.
        """
        for ip in self.private_ips:
            self.subnets.add(iptools.sort(ip))
        if self.network:
            self.location = self.network.locator.locate(self.ips)

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


class IPv4Address(BaseIP, NetworkObject):
    """
    A single IP address found in the network
    """
    addr: str
    node: Node
    subnet: str
    _ptr: set[Tuple[str, str]]
    implied_ptr: set[str]
    nat: str
    location: str
    unused: bool

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
            raise ValueError('Invalid domain')

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


class Node(NetworkObject):
    """
    A Node on the network representing one machine/VM/Kubelet/etc.
    Name should be the FQDN of the machine unless it has a non-default type.
    """
    name: str
    private_ip: str
    docid: str
    public_ips: set
    domains: set
    type: str
    location: str

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


#############################
# Network Object Containers #
#############################

class NetworkObjectContainer(ABC):
    """
    Container for a set of network objects
    """
    objectType: str
    objects: dict
    network: Network

    def __init__(self, objectSet: list[NetworkObject] = [], network: Network = None) -> None:
        self.objects = {object.name: object for object in objectSet}
        self.network = network

    def __getitem__(self, key: str) -> NetworkObject:
        return self.objects[key]

    def __setitem__(self, key: str, value: NetworkObject) -> None:
        self.objects[key] = value

    def __delitem__(self, key: str) -> None:
        del self.objects[key]

    def __iter__(self) -> Iterator[NetworkObject]:
        yield from self.objects.values()

    def __contains__(self, key: str) -> bool:
        return self.objects.__contains__(key)

    def to_json(self) -> str:
        """
        Serialises the set of NetworkObjects to a JSON string using the JSONEncoder defined in this file.

        :return: A string of JSON
        :rtype: str
        """
        return json.dumps({
            'objectType': self.objectType,
            'objects': [object for object in self]
        }, indent = 2, cls = JSONEncoder)

    def add(self, object: NetworkObject) -> None:
        """
        Add a single NetworkObject to the set, merge if an object with that name is already present.

        :param object: The NetworkObject to add to the set.
        :type object: NetworkObject
        """
        if object.name in self:
            self[object.name] = object.merge(self[object.name])
        else:
            object.container = self
            if self.network:
                object.network = self.network
            self[object.name] = object

    def replace(self, identifier: str, object: NetworkObject) -> None:
        """
        Replace the object with the specified identifier with a new object.
        Calls merge on the new object with the object to be replaced passed as the argument.
        If target object is not in the set, the new object is simply added as-is.

        :param identifier: The string to use to identify the existing object to replace.
        :type identifier: str
        :param object: The object to replace the existing object with.
        :type object: NetworkObject
        """
        if identifier in self:
            self.add(object.merge(self[identifier]))
            del self[identifier]
        else:
            self.add(object)


class DomainSet(NetworkObjectContainer):
    """
    Container for a set of Domains
    """
    objectType: str = 'domains'
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
        return self.roles['exclusions']

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

class IPv4AddressSet(NetworkObjectContainer):
    """
    Container for a set of IPv4Address
    """
    objectType: str = 'ips'
    private_ips: list
    public_ips: list
    subnets: set

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


######################
# The Network Object #
######################

class Network:
    """
    Container for sets of network objects.
    """
    domains: DomainSet
    ips: IPv4AddressSet
    nodes: NodeSet
    records: dict
    config: dict
    roles: dict

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
        
        self.config = config or utils.DEFAULT_CONFIG
        self.locator = Locator()

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


    def writeSet(self, set: str, path: str) -> None:
        """
        Serialises a set of NetworkObjects to json writes the json to a file.

        :param set: The atribute name of the set to serialise, one of: 'domains', 'ips', or 'nodes'.
        :type set: str
        :param path: The path to write the JSON to.
        :type path: str
        :raises ValueError: If the *set* parameter cannot be evaluated as an attribute of this Network.
        """
        if hasattr(self, set) and isinstance(getattr(self, set), NetworkObjectContainer):
            with open(path, 'w') as stream:
                stream.write(getattr(self, set).to_json())
        else:
            raise ValueError(f'Unknown set to serialise: {set}')

    def dumpNetwork(self) -> None:
        """
        Writes the domains, ips, and nodes of a network to their default locations.
        """
        self.writeSet('domains', 'src/domains.json')
        self.writeSet('ips', 'src/ips.json')
        self.writeSet('nodes', 'src/nodes.json')

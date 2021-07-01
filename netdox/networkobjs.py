from __future__ import annotations

import json
import re
from datetime import datetime
from abc import ABC, abstractmethod
from collections import defaultdict
from ipaddress import IPv4Address as BaseIP
from typing import Any, Iterable, Tuple, Union

import iptools

dns_name_pattern = re.compile(r'([a-zA-Z0-9_-]+\.)+[a-zA-Z0-9_-]+')

#################
# Location Data #
#################

class Locator:
    """
    Holds the location data for network objects
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

    def __iter__(self):
        yield from self.location_map.keys()

    def locate(self, ip_set: Union[iptools.ipv4, str, Iterable]) -> str:
        """
        Returns a location for an ip or set of ips, or None if there is no determinable location.
        Locations are decided based on the content of the ``locations.json`` config file (for more see :ref:`config`)

        :Returns:
            String|None; A string containing the location as it appears in ``locations.json``, or None if no valid location could be decided on.
        """
        if isinstance(ip_set, iptools.ipv4):
            if ip_set.valid:
                ip_set = [ip_set.ipv4]
            else:
                raise ValueError(f'Invalid IP in set: {ip_set.raw}')
        elif isinstance(ip_set, str):
            if iptools.valid_ip(ip_set):
                ip_set = [ip_set]
            else:
                raise ValueError(f'Invalid IP in set: {ip_set}')
        elif isinstance(ip_set, Iterable):
            for ip in ip_set:
                if not iptools.valid_ip(ip):
                    raise ValueError(f'Invalid IP in set: {ip}')
        else:
            raise TypeError(f'IP set must be one of: str, Iterable[str]; Not {type(ip_set)}')

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


###################
# Network Objects #
###################

class NetworkObject(ABC):
    name: str
    docid: str
    _network: Network
    location: str

    @property
    def network(self):
        return self._network

    @network.setter
    @abstractmethod
    def network(self, new_network: Network):
        self._network = new_network
        self.location = new_network.locator.locate(self)
    
    @abstractmethod
    def merge(self, object: NetworkObject) -> None:
        """
        In place merge of two NetworkObject instances of the same type.
        This method should be called on the object already existing in the set.
        """
        pass


class Domain(NetworkObject):
    """
    A domain defined in a managed DNS server.
    Contains all A/CNAME DNS records from managed servers using this domain as the record name.
    """
    name: str
    root: str
    location: str
    role: str

    def __init__(self, name: str, root: str = None, role: str = None):
        if re.fullmatch(dns_name_pattern, name):
            self.name = name.lower()
            self.docid = f'_nd_domain_{self.name.replace(".","_")}'
            self.root = root.lower() if root else None
            self.role = role.lower() if role else None
            self.location = None

            # destinations
            self._public_ips = set()
            self._private_ips = set()
            self._cnames = set()

            self.subnets = set()
        else:
            raise ValueError('Must provide a valid name for dns record (some FQDN)')

    @classmethod
    def from_dict(cls, object: dict):
        """
        Instantiates a Domain from a dictionary.
        """
        record = cls(object['name'])
        for k, v in object.items():
            setattr(record, k, v)

        for attr in ('_public_ips','_private_ips','_cnames'):
            for destination, source in record.__dict__[attr]:
                record.link(destination, source)

        record.subnets = set(record.subnets)
        record.update()
        
        return record

    def link(self, destination: Union[Domain, IPv4Address, str], source: str):
        """
        Adds a DNS record from this domain to the provided destination.
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
    def destinations(self) -> dict:
        """
        Property: returns a dictionary of all outgoing links from this record.
        """
        return self.public_ips + self.private_ips + self.cnames

    @property
    def _ips(self) -> set[Tuple[str, str]]:
        return self._public_ips.union(self._private_ips)

    @property
    def public_ips(self) -> list[str]:
        """
        Property: returns all IPs from this record that are outside of protected ranges.
        """
        return list(set([ip for ip,_ in self._public_ips]))

    @property
    def private_ips(self) -> list[str]:
        """
        Property: returns all IPs from this record that are inside a protected range.
        """
        return list(set([ip for ip,_ in self._private_ips]))

    @property
    def ips(self) -> list[str]:
        """
        Property: returns all IPs from this record.
        """
        return list(set(self.public_ips + self.private_ips))

    @property
    def cnames(self) -> list[str]:
        """
        Property: returns all CNAMEs from this record.
        """
        return list(set([cname for cname,_ in self._cnames]))

    def update(self):
        """
        Updates subnet and location data for this record.
        """
        for ip in self.private_ips:
            self.subnets.add(iptools.sort(ip))
        if self.network:
            self.location = self.network.locator.locate(self.ips)

    @property
    def network(self):
        return self._network

    @network.setter
    def network(self, new_network: Network):
        self._network = new_network
        self.location = new_network.locator.locate(self.ips)

    def merge(self, domain: Domain) -> None:
        """
        In place merge of two Domain objects
        This method should be called on the object already existing in the set.
        """
        if self.name == domain.name:
            self._private_ips = domain._private_ips | self._private_ips
            self._public_ips = domain._public_ips | self._public_ips
            self._cnames = domain._cnames | self._cnames
            self.update()
        else:
            raise ValueError('Cannot merge two Domains with different names')


class IPv4Address(BaseIP, NetworkObject):
    """
    A single IP address found in the network
    """
    addr: str
    name: str
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
        self._ptr = set()
        self.implied_ptr = set()
        self.nat = None
        self.unused = unused

    @property
    def ptr(self):
        """
        A list of domains this IP address points to
        """
        return sorted([domain for domain, _ in self._ptr])

    @property
    def domains(self):
        """
        The superset of domains this IP points to, and domains which point back.
        """
        return sorted(set(self.ptr).union(self.implied_ptr))

    @property
    def network(self):
        return self._network

    @network.setter
    def network(self, new_network: Network):
        self._network = new_network
        self.location = new_network.locator.locate(self.addr)

    def merge(self, ip: IPv4Address) -> None:
        """
        In place merge of two IPv4Address objects
        This method should be called on the object already existing in the set.
        """
        if self.addr == ip.addr:
            self._ptr = ip._ptr | self._ptr
            self.implied_ptr = ip.implied_ptr | self.implied_ptr
            self.nat = self.nat or ip.nat
        else:
            raise ValueError('Cannot merge two IPv4Addresses with different names')

    def link(self, domain: Union[Domain, str], source: str):
        """
        Adds a PTR record from this IP address to some domain
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

        self.name = name
        self.docid = f'_nd_node_{self.name.replace(".","_")}'
        if iptools.valid_ip(private_ip):
            self.private_ip = private_ip
        else:
            raise ValueError(f'Invalid private IP {private_ip}')
        self.docid = f'_nd_node_{self.private_ip.replace(".","_")}'
        self.public_ips = set(public_ips) or set()
        self.domains = set(domains) or set()
        self.type = type

    @property
    def ips(self):
        return list(self.public_ips) + [self.private_ip]

    @property
    def network(self):
        return self._network

    @network.setter
    def network(self, new_network: Network):
        self._network = new_network
        self.location = new_network.locator.locate(self.ips)

    def merge(self, node: Node) -> None:
        """
        In place merge of two Node objects.
        This method should be called on the object already existing in the set.
        """
        if self.type == node.type and self.private_ip == node.private_ip:
            self.public_ips = node.public_ips | self.public_ips
            self.domains = node.domains | self.domains
            if self.network:
                self.location = self.network.locator.locate(self.ips)
        else:
            raise TypeError('Cannot merge two Nodes of different types')


###############################
# Network Object JSON Encoder #
###############################

class JSONEncoder(json.JSONEncoder):
    """
    JSON Encoder compatible with NetworkObjects, sets, and datetime objects
    """
    def default(self, obj):
        """
        :meta private:
        """
        if isinstance(obj, NetworkObject):
            return obj.__dict__ | {'_network': None}
        elif isinstance(obj, set):
            return sorted(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return super().default(obj)


#############################
# Network Object Containers #
#############################

class NetworkObjectContainer(ABC):
    """
    Container for a set of network objects
    """
    objectType: str
    objects: dict
    names: list

    def __init__(self, objectSet: list = [], network: Network = None) -> None:
        self.objects = {object.name: object for object in objectSet}
        self.network = network

    def __getitem__(self, key: str) -> Any:
        return self.objects[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.objects[key] = value

    def __delitem__(self, key: str) -> None:
        del self.objects[key]

    def __iter__(self) -> Any:
        yield from self.objects.values()

    def __contains__(self, key: str) -> bool:
        return self.objects.__contains__(key)

    @property
    def names(self) -> list[str]:
        return list(self.objects.keys())

    def to_json(self) -> str:
        return json.dumps({
            'objectType': self.objects,
            'objects': [object for object in self]
        }, indent = 2, cls = JSONEncoder)

    def add(self, object: NetworkObject) -> None:
        """
        Add a single network object to the set, merge if an object with that name is already present.
        """
        if object.name in self:
            self[object.name] = self[object.name].merge(object)
        else:
            if self.network:
                object.network = self.network
            self[object.name] = object


class DomainSet(NetworkObjectContainer):
    """
    Container for a set of Domains
    """
    objectType: str = 'domains'

    @property
    def domains(self) -> dict:
        return self.objects

class IPv4AddressSet(NetworkObjectContainer):
    """
    Container for a set of IPv4Address
    """
    objectType: str = 'ips'
    private_ips: list
    public_ips: list
    subnets: set

    def __init__(self, ips: list[IPv4Address] = []) -> None:
        self.objects = {ip.addr: ip for ip in ips}
        self.subnets = set()

    def add(self, ip: IPv4Address) -> None:
        """
        Add a single IPv4Address to the set, merge if that IP is already in the set. 
        Add the /24 bit subnet to the set of subnets.
        """
        super().add(ip)
        if ip.is_private:
            self.subnets.add(ip.subnetFromMask())

    @property
    def ips(self) -> dict:
        return self.objects

    @property
    def private_ips(self) -> list[IPv4Address]:
        return [ip for ip in self if ip.is_private]

    @property
    def public_ips(self) -> list[IPv4Address]:
        return [ip for ip in self if not ip.is_private]

    @property
    def unused(self) -> list[IPv4Address]:
        return [ip for ip in self if ip.unused]

    @property
    def used(self) -> list[IPv4Address]:
        return [ip for ip in self if not ip.unused]

    def fillSubnets(self) -> None:
        for subnet in self.subnets:
            for ip in iptools.subn_iter(subnet):
                if ip not in self:
                    self[ip] = IPv4Address(ip, True)

class NodeSet(NetworkObjectContainer):
    """
    Container for a set of Nodes
    """
    objectType: str = 'nodes'

    @property
    def nodes(self) -> dict:
        return self.objects


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

    def __init__(self, 
            domains: DomainSet = None, 
            ips: IPv4AddressSet = None, 
            nodes: NodeSet = None,
            config: dict = None
        ) -> None:

        self.domains = domains or DomainSet()
        self.domains.network = self

        self.ips = ips or IPv4AddressSet()
        self.ips.network = self
        
        self.nodes = nodes or NodeSet()
        self.nodes.network = self
        
        self.config = config or {'exclusions': []}
        self.locator = Locator()

    def __contains__(self, object: str) -> bool:
        return (
            self.domains.__contains__(object) or
            self.ips.__contains__(object) or
            self.nodes.__contains__(object)
        )

    def add(self, object: NetworkObject) -> None:
        """
        Add a NetworkObject to the network
        """
        if isinstance(object, Domain):
            self.domains.add(object)
        elif isinstance(object, IPv4Address):
            self.ips.add(object)
        elif isinstance(object, Node):
            self.nodes.add(object)

    def addSet(self, object_set: NetworkObjectContainer) -> None:
        """
        Add a set of network objects to the network

        2do: Implement merge in NetworkObjectContainer ABC
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
    def exclusions(self) -> list[str]:
        return self.config['exclusions']

    @property
    def roles(self) -> dict:
        return {k: v for k, v in self.config.items() if k != 'exclusions'}

    def applyDomainRoles(self) -> None:
        """
        Sets the role attribute on domains in the network DomainSet where possible
        """
        if self.config:
            for role, roleConfig in self.config.items():
                if role == 'exclusions':
                    for domain in roleConfig:
                        if domain in self.domains:
                            del self.domains[domain]
                else:
                    for domain in roleConfig['domains']:
                        if domain in self.domains:
                            self.domains[domain].role = role
        
        for domain in self.domains:
            if domain.role is None:
                domain.role = 'default'

    @property
    def records(self) -> dict:
        f_implied = defaultdict([])
        for ip in self.ips:
            for domain in ip.domains:
                f_implied[domain].append(ip)

        r_implied = defaultdict([])
        for domain in self.domains:
            for ip in domain.ips:
                r_implied[ip].append(domain)

        return {
            'forward': {domain.name: domain.destinations for domain in self.domains},
            'reverse': {ip.addr: ip.ptr for ip in self.ips}
        }

    def discoverImpliedPTR(self) -> None:
        for domain, ips in self.records['forward'].items():
            for ip in ips:
                if ip in self.ips:
                    self.ips[ip].implied_ptr.add(domain)

    def writeSet(self, set: str, path: str) -> None:
        """
        Serialises a set of NetworkObjects to json writes the json to a file.
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

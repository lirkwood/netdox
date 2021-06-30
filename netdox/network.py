from __future__ import annotations

import re, json
from abc import ABC, abstractmethod
from ipaddress import IPv4Address as BaseIP
from typing import Any, Iterable, Tuple, Union

import iptools
from utils import dns_name_pattern, locate

###################
# Network Objects #
###################

class NetworkObject(ABC):
    name: str
    
    @abstractmethod
    def merge(self, object: NetworkObject) -> None:
        """
        In place merge of two NetworkObject instances of the same type.
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

    def __init__(self, name: str, root: str = None):
        if re.fullmatch(dns_name_pattern, name):
            self.name = name.lower()
            self.root = root.lower() if root else None
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
        return {
            'public_ips': self.public_ips,
            'private_ips': self.private_ips,
            'cnames': self.cnames,
        }

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
        self.location = locate(self.ips)

    def merge(self, domain: Domain) -> None:
        """
        In place merge of two Domain objects
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

    def __init__(self, address: object) -> None:
        super().__init__(address)
        self.addr = str(address)
        self.name = self.addr
        self._ptr = set()
        self.implied_ptr = set()
        self.nat = None
        self.location = locate(self)

    @property
    def ptr(self):
        """
        A list of domains this IP address points to
        """
        return [domain for domain, _ in self._ptr]

    @property
    def domains(self):
        """
        The superset of domains this IP points to, and domains which point back.
        """
        return list(set(self.ptr) + self.implied_ptr)

    def merge(self, ip: IPv4Address) -> None:
        """
        In place merge of two IPv4Address objects
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
    ip: str
    domain: str
    type: str
    location: str

    def __init__(self, 
            name: str, 
            private_ips: Iterable[str] = None, 
            public_ips: Iterable[str] = None, 
            domains: Iterable[str] = None, 
            type: str = 'default'
        ) -> None:

        self.name = name
        self.private_ips = set(private_ips) or set()
        self.public_ips = set(public_ips) or set()
        self.domains = set(domains) or set()
        self.type = type
        self.location = locate(self.ips)

    @property
    def ips(self):
        return list(set(self.private_ips + self.public_ips))

    @ips.setter
    def ips(self, iplist: Iterable[str]):
        self.public_ips = set()
        self.private_ips = set()
        for ip in iplist:
            if iptools.valid_ip(ip):
                if iptools.public_ip(ip):
                    self.public_ips.add(ip)
                else:
                    self.private_ips.add(ip)
            else:
                raise ValueError(f'Invalid IP address: {ip}')
        self.location = locate(self.ips)

    def merge(self, node: Node) -> None:
        """
        In place merge of two Node objects
        """
        if self.type == node.type:
            self.private_ips = node.private_ips | self.private_ips
            self.public_ips = node.public_ips | self.public_ips
            self.domains = node.domains | self.domain
            self.location = locate(self.ips)
        else:
            raise TypeError('Cannot merge two Nodes of different types')


#############################
# Network Object Containers #
#############################

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
        self.ips = ips or IPv4AddressSet()
        self.nodes = nodes or NodeSet()
        self.config = config or {'exclusions': []}

    def add(self, object: NetworkObject) -> None:
        if isinstance(object, Domain):
            self.domains.add(object)
        elif isinstance(object, IPv4Address):
            self.ips.add(object)
        elif isinstance(object, Node):
            self.nodes.add(object)

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
            for domain in self.domains:
                if domain in self.config['exclusions']:
                    del self.domains[domain]
                else:
                    for role in self.roles:
                        if domain in role['domains']:
                            domain.role = role

    @property
    def records(self) -> dict:
        return {
            'forward': {domain.name: domain.destinations for domain in self.domains},
            'reverse': {ip.addr: ip.ptr for ip in self.ips}
        }


class NetworkObjectContainer(ABC):
    """
    Container for a set of network objects
    """
    objectType: str
    objects: dict
    names: list

    def __init__(self, objectSet: list = []) -> None:
        self.objects = {object.name for object in objectSet}

    def __getitem__(self, key: str) -> Any:
        return self.objects[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.objects[key] = value

    def __delitem__(self, key: str) -> None:
        del self.objects[key]

    def __iter__(self) -> Any:
        for _, value in self.objects.items():
            yield value

    def __contains__(self, key: str) -> bool:
        return self.objects.__contains__(key)

    @property
    def names(self) -> list[str]:
        return list(self.objects.keys())

    def to_json(self) -> str:
        return json.dumps({
            'objectType': self.objects,
            'objects': [object.__dict__ for object in self]
        })

    def add(self, object: NetworkObject) -> None:
        if object.name in self:
            self[object.name] = self[object.name].merge(object)
        else:
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

    @property
    def ips(self) -> dict:
        return self.objects

    @property
    def private_ips(self) -> list[IPv4Address]:
        return [ip for ip in self if ip.is_private]

    @property
    def public_ips(self) -> list[IPv4Address]:
        return [ip for ip in self if not ip.is_private]

    def fillSubnets(self) -> None:
        for ip in self.private_ips:
            subnet = ip.subnetFromMask(24)
            self.subnets.add(subnet)

class NodeSet(NetworkObjectContainer):
    """
    Container for a set of Nodes
    """
    objectType: str = 'nodes'

    @property
    def nodes(self) -> dict:
        return self.objects
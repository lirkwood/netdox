from __future__ import annotations

import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Generic, Iterable, Iterator, Optional, TypeVar, Union

from bs4 import BeautifulSoup
from bs4.element import Tag

from netdox import base, containers, iptools, nodes, utils
from netdox.psml import (DOMAIN_TEMPLATE, IPV4ADDRESS_TEMPLATE,
                         PropertiesFragment, Property, Section, XRef)


class DNSRecordType(Enum):
    A = 'A'
    CNAME = 'CNAME'
    PTR = 'PTR'

    def __str__(self) -> str:
        return self.value

@dataclass(frozen = True)
class DNSRecord:
    """Represents a DNS record."""
    origin: DNSObject
    """The DNSObject the link points from."""
    destination: DNSObject
    """The DNSObject the record points to."""
    source: str
    """The name of the plugin that provided this record."""
    type: DNSRecordType
    """The type of this DNS record."""
    hash: int
    """Pre-calculated hash of origin/dest name and source. Necessary for pickling."""

    def __init__(self, origin: DNSObject, destination: DNSObject, source: str) -> None:
        object.__setattr__(self, 'origin', origin)
        object.__setattr__(self, 'destination', destination)
        object.__setattr__(self, 'source', source)

        object.__setattr__(self, 'hash', hash(
            (origin.name, destination.name, source)))
        object.__setattr__(self, 'type', 
            RECORD_TYPE_MAP[(origin.type, destination.type)])

    def __hash__(self) -> int:
        return self.hash

    def __eq__(self, other) -> bool:
        return (
            self.origin.name == other.origin.name and
            self.destination.name == other.destination.name and
            self.source == other.source
        )

@dataclass(frozen = True)
class NATEntry:
    """Represents a NAT entry, linking one IPv4 to another."""
    origin: IPv4Address
    """The IPv4Address the record points from."""
    destination: IPv4Address
    """The IPv4Address the record points to."""
    source: str
    """The name of the plugin that provided this record."""
    hash: int
    """Pre-calculated hash of origin/dest name and source. Necessary for pickling."""

    def __init__(self, origin: DNSObject, destination: DNSObject, source: str) -> None:
        object.__setattr__(self, 'origin', origin)
        object.__setattr__(self, 'destination', destination)
        object.__setattr__(self, 'source', source)

        object.__setattr__(self, 'hash', hash(
            (origin.name, destination.name, source)))

    def __hash__(self) -> int:
        return self.hash

    def __eq__(self, other) -> bool:
        return (
            self.origin.name == other.origin.name and
            self.destination.name == other.destination.name and
            self.source == other.source
        )

class DNSRecordSet:
    #TODO profile mem usage with instance of this on each dnsobj
    """Container for DNSRecords."""
    _set: set[DNSRecord]

    def __init__(self, records: Iterable[DNSRecord] = None) -> None:
        self._set = set(records) if records else set()

    def __iter__(self) -> Iterator[DNSRecord]:
        yield from self._set

    def __contains__(self, key: DNSRecord) -> bool:
        return key in self._set

    def __getitem__(self, key: DNSRecordType) -> DNSRecordSet:
        return getattr(self, key.value)

    def add(self, record: DNSRecord) -> None:
        self._set.add(record)

    def remove(self, record: DNSRecord) -> None:
        self._set.remove(record)

    def union(self, other: DNSRecordSet) -> DNSRecordSet:
        """Returns a new DNSRecordSet containing all records from both sets."""
        return DNSRecordSet(self._set | other._set)

    def difference(self, other: DNSRecordSet) -> DNSRecordSet:
        """Returns a new DNSRecordSet without any records from the other set."""
        return DNSRecordSet(self._set - other._set)

    def to_psml(self, implied: bool = False) -> Section:
        """
        Returns a section tag containing the records in this set.

        :param implied: Whether this recordset is tracking implied records, 
        defaults to False
        :type implied: bool, optional
        :return: A PSML section tag.
        :rtype: Tag
        """
        id_prefix = 'implied_' if implied else ''
        title_prefix = 'Implied ' if implied else ''
        root = Section(id_prefix + 'records', title_prefix + 'DNS Records')
        
        for record_type in DNSRecordType:
            for count, record in enumerate(self[record_type]):
                dest = record.destination
                root.insert(PropertiesFragment(
                    id = id_prefix + f'{record_type}_record_{count}', 
                    properties = [
                        Property(dest.type, XRef(docid = dest.docid), 
                            title_prefix + f'{record_type} record'),
                        Property('source', record.source, 'Source Plugin')
                ]))

        return root
        

    # Record types

    @property
    def A(self) -> DNSRecordSet:
        """Returns a new record set with all DNSRecords of type 'A'."""
        return DNSRecordSet(
            {record for record in self if record.type == DNSRecordType.A})

    @property
    def PTR(self) -> DNSRecordSet:
        """Returns a new record set with all DNSRecords of type 'PTR'"""
        return DNSRecordSet(
            {record for record in self if record.type == DNSRecordType.PTR})

    @property
    def CNAME(self) -> DNSRecordSet:
        """Returns a new record set with all DNSRecords of type 'CNAME'"""
        return DNSRecordSet(
            {record for record in self if record.type == DNSRecordType.CNAME})

    # Record attributes

    @property
    def destinations(self) -> set[DNSObject]:
        """Returns all destinations in the set."""
        return {record.destination for record in self}

    @property
    def names(self) -> set[str]:
        """Returns all destination names in the set."""
        return {record.destination.name for record in self}

    @property
    def sources(self) -> set[str]:
        """Returns all sources in the set."""
        return {record.source for record in self}


class DNSObject(base.NetworkObject):
    """
    A NetworkObject representing an object in a managed DNS zone.
    """
    zone: Optional[str]
    """The DNS zone this object is from."""
    records: DNSRecordSet
    """A set of DNSRecords originating from this object."""
    backrefs: DNSRecordSet
    """Like records but stores DNSRecords resolving to this object."""
    _node: Optional[Union[nodes.Node, nodes.NodeProxy]]
    """The node/proxy this DNSObject resolves to."""

    ## dunder methods

    def __init__(self, network: containers.Network, name: str, zone: str = None, labels: Iterable[str] = None) -> None:
        super().__init__(network, name, name, labels)
        self.zone = zone.lower() if zone else zone
        self.node = None
        self.records = DNSRecordSet()
        self.backrefs = DNSRecordSet()

    ## abstract properties

    @property
    def docid(self) -> str:
        return f'_nd_{self.type}_{self.name.replace(".","_")}'

    ## methods

    def link(self, destination: Union[str, DNSObject], source: str) -> None:
        """
        Adds a record from this object to a DNSObject at *destination*.
        Also creates a record in the *destination* backrefs.

        :param destination: The name of the DNSObject to link to, or the object itself.
        :type destination: Union[str, DNSObject]
        :param source: The plugin that provided this link.
        :type source: str
        """
        if isinstance(destination, str):
            destination = self.network.find_dns(destination)
        self.records.add(DNSRecord(self, destination, source))
        destination.backrefs.add(DNSRecord(destination, self, source))

    def to_psml(self) -> BeautifulSoup:
        soup = super().to_psml()
        header = soup.find('properties-fragment', id = 'header')
        header.append(Property(
            name = 'node',
            title = 'Node',
            value = XRef(docid = self.node.docid) if self.node else '???'
        ).tag)

        if self.node is not None and isinstance(self.node, nodes.ProxiedNode):
            proxy_value: Union[str, XRef]
            if self.node.proxy.node:
                proxy_value = XRef(docid = self.node.proxy.node.docid)
            else:
                proxy_value = 'Not Provided'
            header.append(Property('proxy', proxy_value, 'Proxy').tag)
        
        soup.find('section', id = 'records').replace_with(self.records.to_psml().tag)
        soup.find('section', id = 'implied_records').replace_with(
            self.backrefs.difference(self.records).to_psml(implied = True).tag)

        return soup

    def merge(self, object: DNSObject) -> DNSObject: # type: ignore
        """
        In place merge of two DNSObjects of the same type.
        This method should always be called on the object entering the set.
        """
        if object.name == self.name:
            super().merge(object)
            self.records = self.records.union(object.records)
            self.backrefs = self.backrefs.union(object.backrefs)
            return self
        else:
            raise AttributeError('Cannot merge DNSObjects with different names.')

    #TODO add exclusion validation at this level: _enter?

    ## properties

    @property
    def node(self) -> Optional[nodes.Node]:
        """
        Returns the node this object resolves to.
        If *_node* is a NodeProxy, perform a lookup and return the result.
        """
        if self._node is not None and isinstance(self._node, nodes.NodeProxy):
            return self._node.lookup(self.name)
        return self._node

    @node.setter
    def node(self, value: nodes.Node) -> None:
        self._node = value

    @node.deleter
    def node(self) -> None:
        self._node = None

DNSObjT = TypeVar('DNSObjT', bound = DNSObject)

class Domain(DNSObject):
    """
    A domain defined in a managed DNS zone.
    Contains all A/CNAME DNS records from managed zones 
    using this domain as the record name.
    """
    type = 'domain'
    TEMPLATE = DOMAIN_TEMPLATE
    
    ## dunder methods

    def __init__(self, 
            network: containers.Network, 
            name: str, 
            zone: str = None, 
            labels: Iterable[str] = None
        ) -> None:
        """
        Initialises a Domain and adds it to *network*.

        :param name: The domain name to use
        :type name: str
        :param zone: The parent DNS zone, defaults to None
        :type zone: str, optional
        :raises ValueError: If *name* is not a valid FQDN
        """
        if utils.valid_domain(name):

            super().__init__(
                network = network, 
                name = name, 
                zone = zone or utils.root_domain(name),
                labels = labels
            )
            
        else:
            raise ValueError('Must provide a valid name for a Domain (some FQDN)')
    
    ## abstract properties

    @property
    def search_terms(self) -> list[str]:
        tokenized = self.name.split('.')
        return tokenized + [
            '.'.join(tokenized[i + 1:]) for i in range(len(tokenized) - 1)
        ]

    @property
    def outpath(self) -> str:
        return os.path.normpath(os.path.join(utils.APPDIR, f'out/domains/{self.docid}.psml'))

    @property
    def domains(self) -> set[str]:
        return (self.records.CNAME.names.union(self.backrefs.CNAME.names)).union(
            [self.name])

    @property
    def ips(self) -> set[str]:
        return self.records.A.names.union(self.backrefs.PTR.names)
    
    ## abstract methods

    def merge(self, other: Domain) -> Domain: # type: ignore
        super().merge(other)
        return self

    def _enter(self) -> Domain:
        """
        Adds this Domain to the network's DomainSet.

        :return: The name of this Domain.
        :rtype: str
        """
        if self.name in self.network.domains:
            self.network.domains[self.name] = self.merge(self.network.domains[self.name])
        else:
            self.network.domains[self.name] = self
        return self

    ## properties

    @property
    def subnets(self) -> set[str]:
        """Returns a set of IPv4 CIDR 8-bit subnets that this domain resolves to."""
        return {iptools.sort(ip) for ip in self.ips}

class IPv4Address(DNSObject):
    """
    A single IP address found in the network
    """
    subnet: str
    """The 24 bit CIDR subnet this IP is in."""
    is_private: bool
    """Whether or not this IP is private"""
    NAT: set[NATEntry]
    """A set of NAT entries."""
    type = 'ipv4'
    TEMPLATE = IPV4ADDRESS_TEMPLATE
    
    ## dunder methods

    def __init__(self, 
        network: containers.Network, 
        address: str,
        labels: Iterable[str] = None
    ) -> None:

        if iptools.valid_ip(address):
            super().__init__(
                network = network, 
                name = address, 
                zone = '.'.join(address.split('.')[-2::-1])+ '.in-addr.arpa',
                labels = labels
            )

            self.is_private = not iptools.public_ip(self.name)
            self.subnet = self.subnetFromMask()
            self.NAT = set()
        else:
            raise ValueError('Must provide a valid name for an IPv4Address (some IPv4, in CIDR form)')

    ## abstract properties

    @property
    def outpath(self) -> str:
        return os.path.normpath(os.path.join(
            utils.APPDIR, 'out/ips', self.subnet.replace("/","_"), self.docid + '.psml'
        ))

    @property
    def ips(self) -> set[str]:
        return (self.records.CNAME.names.union(self.backrefs.CNAME.names)).union(
            [self.name])

    @property
    def domains(self) -> set[str]:
        return (self.records.PTR.names.union(self.backrefs.A.names))
    
    ## abstract methods

    def translate(self, destination: Union[str, IPv4Address], source: str) -> None:
        """
        Adds a NAT entry to pointing to *destination*.

        :param destination: The IPv4Address to translate this IP to.
        :type destination: Union[str, IPv4Address]
        :param source: The plugin that provided this NAT entry.
        :type source: str
        """
        if isinstance(destination, str):
            destObj = self.network.ips[destination]
        else:
            destObj = destination
        
        self.NAT.add(NATEntry(self, destObj, source))
        destObj.NAT.add(NATEntry(destObj, self, source))

    def _enter(self) -> IPv4Address:
        """
        Adds this IPv4Address to the network's IPv4AddressSet.

        :return: The name of this IP.
        :rtype: str
        """
        if self.name in self.network.ips:
            self.network.ips[self.name] = self.merge(self.network.ips[self.name])
        else:
            self.network.ips[self.name] = self
        if self.is_private:
            self.network.ips.subnets.add(self.subnetFromMask())
        return self

    def to_psml(self) -> BeautifulSoup:
        soup = super().to_psml()
        body = soup.find('section', id = 'records')
        for count, record in enumerate(self.NAT):
            dest = record.destination
            body.append(PropertiesFragment(f'NAT_{count}', [
                Property(dest.type, XRef(docid = dest.docid), 'NAT Entry'),
                Property('source', record.source, 'Source Plugin')
            ]).tag)

        return soup

    def merge(self, ip: IPv4Address) -> IPv4Address: # type: ignore
        """
        In place merge of two IPv4Address instances.
        This method should always be called on the object entering the set.

        :param ip: The IPv4Address to merge with.
        :type ip: IPv4Address
        :raises ValueError: If the IPv4Address objects cannot be merged (if their addr attributes are not equal).
        :return: This IPv4Address object, which is now a superset of the two.
        :rtype: IPv4Address
        """
        super().merge(ip)
        self.NAT |= ip.NAT
        return self

    ## properties

    @property
    def unused(self) -> bool:
        """
        Returns False if this object is pointing to any other objects, or is being pointed at.
        True otherwise.
        """
        return not bool(
            self.records.names or
            self.backrefs.names or
            self.node
        )

    ## methods

    def subnetFromMask(self, mask: str = '24') -> str:
        """
        Return the subnet of a given size containing this IP

        :param mask: The subnet mask to use in bits, defaults to '24'
        :type mask: Union[str, int], optional
        :return: A IPv4 subnet in CIDR format
        :rtype: str
        """
        subnet = f'{self.name}/{mask}'
        return f'{iptools.subn_floor(subnet)}/{mask}'


RECORD_TYPE_MAP = {
    (Domain.type, IPv4Address.type): DNSRecordType.A, 
    (Domain.type, Domain.type): DNSRecordType.CNAME,
    (IPv4Address.type, IPv4Address.type): DNSRecordType.CNAME,
    (IPv4Address.type, Domain.type): DNSRecordType.PTR
}

## Container

class DNSObjectContainer(base.NetworkObjectContainer[DNSObjT], Generic[DNSObjT]):
    """
    Container for a set of DNSObjects.
    """

    ## dunder methods

    def __init__(self, network: containers.Network, objects: Iterable[DNSObjT] = []) -> None:
        self.network = network
        self.objects = {object.name: object for object in objects}

    def __getitem__(self, key: str) -> DNSObjT:
        if key not in self.objects:
            self.objects[key] = self.objectClass(self.network, key)
        return super().__getitem__(key)

    def __contains__(self, key: Union[str, DNSObjT]) -> bool:
        if isinstance(key, str):
            return super().__contains__(key)
        else:
            return super().__contains__(key.name)

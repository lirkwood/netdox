from __future__ import annotations
from abc import ABC, abstractmethod

import os
from dataclasses import dataclass
from enum import Enum
from typing import Generic, Iterable, Iterator, Optional, TypeVar, Union

from bs4 import BeautifulSoup

from netdox import base, containers, iptools, nodes, utils
from netdox.helpers import CountedFacets
from netdox.psml import (DOMAIN_TEMPLATE, IPV4ADDRESS_TEMPLATE, Fragment,
                         PropertiesFragment, Property, Section, XRef)

class DNSRecordType(Enum):
    A = 'A'
    CNAME = 'CNAME'
    PTR = 'PTR'
    TXT = 'TXT'
    CAA = 'CAA'

    def __str__(self) -> str:
        return self.value

    def is_link(self) -> bool:
        """Returns true if this DNSRecordType can describe a DNSLink."""
        return (self != DNSRecordType.TXT) & (self != DNSRecordType.CAA)

    @staticmethod
    def links() -> list[DNSRecordType]:
        """Returns a list of DNSRecordTypes that can describe DNSLinks."""
        return [DNSRecordType.A, DNSRecordType.CNAME, DNSRecordType.PTR]

@dataclass(frozen = True) # type: ignore
class DNSRecord(ABC):
    """Represents a DNS record."""
    name: str
    """Name of this DNS record."""
    value: str
    """Value returned for this DNS record."""
    source: str
    """Name of the plugin that provided this record."""
    type: DNSRecordType
    """The type of this DNS record."""
    hash: int
    """Pre-calculated hash of origin/dest name and source. Necessary for pickling."""

    def __init__(self, name: str, value: str, source: str, type: DNSRecordType) -> None:
        object.__setattr__(self, 'name', name)
        object.__setattr__(self, 'value', value)
        object.__setattr__(self, 'source', source)
        object.__setattr__(self, 'type', type)
        object.__setattr__(self, 'hash', hash((name, value, source)))

    def __hash__(self) -> int:
        return self.hash

    def __eq__(self, other) -> bool:
        return self.__hash__() == other.__hash__()
    
    @abstractmethod
    def to_psml(self, id: str) -> PropertiesFragment:
        """
        Returns a PropertiesFragment describing this record.

        :param id: ID for the properties fragment.
        :type id: str
        :return: A PropertiesFragment with the given ID.
        :rtype: PropertiesFragment
        """
        ...

class DNSLink(DNSRecord):
    """Represents a DNS record that resolves to another DNSObject.
    Type may be A, CNAME, or PTR."""
    origin: DNSObject
    """The DNSObject the link points from."""
    destination: DNSObject
    """The DNSObject the record points to."""

    def __init__(self, origin: DNSObject, destination: DNSObject, source: str) -> None:
        super().__init__(origin.name, destination.name, source, 
            type = RECORD_TYPE_MAP[(origin.type, destination.type)])
        object.__setattr__(self, 'origin', origin)
        object.__setattr__(self, 'destination', destination)

    def to_psml(self, id: str) -> PropertiesFragment:
        """
        Returns a PropertiesFragment describing this record.

        :param id: ID for the properties fragment.
        :type id: str
        :param implied: Whether this is an implied record.
        :type implied: bool
        :return: A PropertiesFragment with the given ID.
        :rtype: PropertiesFragment
        """
        return PropertiesFragment(
            id = id, 
            properties = [
                Property(
                    self.destination.type, 
                    XRef(docid = self.destination.docid),
                    f'{self.type} record'
                ),
                Property('source', self.source, 'Source Plugin')
        ])

    def to_psml_implied(self, id_suffix: str) -> PropertiesFragment:
        """
        Returns a PropertiesFragment describing this record 
        from the perspective of the destination object.

        In practice this method simply prefixes the provided ID 
        and the property titles with the word 'implied'.

        :param id_suffix: ID for the properties fragment.
        Will be prefixed with 'implied_'
        :type id_suffix: str
        :return: A PropertiesFragment with the given ID suffix.
        :rtype: PropertiesFragment
        """
        return PropertiesFragment(
            id = f'implied_{id_suffix}', 
            properties = [
                Property(
                    self.destination.type, 
                    XRef(docid = self.destination.docid),
                    f'Implied {self.type} record'
                ),
                Property('source', self.source, 'Source Plugin')
        ])

class TXTRecord(DNSRecord):
    "Implementation for TXT DNS records."
    type = DNSRecordType.TXT
    zone: str
    """The domain this record uses as its DNS zone."""

    def __init__(self, name: str, value: str, source: str) -> None:
        super().__init__(name, value, source, self.type)
        object.__setattr__(self, 'zone', '.'.join(name.split('.')[1:]))

    def to_psml(self, id: str) -> PropertiesFragment:
        return PropertiesFragment(id, [
            Property('txt_name', self.name, 'Name'),
            Property('txt_value', self.value, 'Value'),
            Property('source', self.source, 'Source Plugin')
        ])

    @classmethod
    def from_psml(cls, psml: PropertiesFragment) -> TXTRecord:
        record = psml.to_dict()
        return cls(record['txt_name'], record['txt_value'], record['source'])

class CAARecord(DNSRecord):
    "Implementation for CAA DNS records."
    type = DNSRecordType.CAA
    caa_type: str
    """Type of the CAA record."""

    def __init__(self, name: str, value: str, type: str, source: str) -> None:
        super().__init__(name, value, source, self.type)
        object.__setattr__(self, 'caa_type', type)

    def to_psml(self, id: str) -> PropertiesFragment:
        return PropertiesFragment(id, [
            Property('caa_name', self.name, 'Name'),
            Property('caa_value', self.value, 'Value'),
            Property('caa_type', self.caa_type, 'Type'),
            Property('source', self.source, 'Source Plugin')
        ])

    @classmethod
    def from_psml(cls, psml: PropertiesFragment) -> CAARecord:
        record = psml.to_dict()
        return cls(record['caa_name'], record['caa_value'], record['caa_type'], record['source'])

class NATLink:
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

    def to_psml(self, id: str) -> PropertiesFragment:
        """
        Returns a PropertiesFragment describing this entry.

        :param id: ID for the properties fragment.
        :type id: str
        :return: A PropertiesFragment with the given ID.
        :rtype: PropertiesFragment
        """
        return PropertiesFragment(
            id = id, 
            properties = [
                Property(
                    self.destination.type,
                    XRef(docid = self.destination.docid),
                    'NAT Entry'),
                Property('source', self.source, 'Source Plugin')
        ])

class DNSLinkSet:
    #TODO profile mem usage with instance of this on each dnsobj
    """Container for DNSRecords."""
    _set: set[DNSLink]

    def __init__(self, records: Iterable[DNSLink] = None) -> None:
        self._set = set(records) if records else set()

    def __iter__(self) -> Iterator[DNSLink]:
        yield from self._set

    def __contains__(self, key: DNSLink) -> bool:
        return key in self._set

    def __getitem__(self, key: DNSRecordType) -> DNSLinkSet:
        return getattr(self, key.value)
    
    def __len__(self) -> int:
        return len(self._set)

    def add(self, record: DNSLink) -> None:
        self._set.add(record)

    def remove(self, record: DNSLink) -> None:
        self._set.remove(record)

    def union(self, other: DNSLinkSet) -> DNSLinkSet:
        """Returns a new DNSRecordSet containing all records from both sets."""
        return DNSLinkSet(self._set | other._set)

    def difference(self, other: DNSLinkSet) -> DNSLinkSet:
        """Returns a new DNSRecordSet without any records from the other set."""
        return DNSLinkSet(self._set - other._set)

    def to_psml(self, implied: bool = False) -> Section:
        """
        Returns a section tag containing the records in this set.

        :param implied: Whether this recordset is tracking implied records, 
        defaults to False
        :type implied: bool, optional
        :return: A PSML section tag.
        :rtype: Tag
        """
        section_id = 'implied_records' if implied else 'records'
        section_title = 'Implied DNS Records' if implied else 'DNS Records'
        root = Section(section_id, section_title)
        
        for record_type in DNSRecordType.links():
            for count, record in enumerate(self[record_type]):
                frag_id = f'{record_type}_record_{count}'
                if implied:
                    root.insert(record.to_psml_implied(frag_id))
                else:
                    root.insert(record.to_psml(frag_id))
        return root
        
    # Record types

    @property
    def A(self) -> DNSLinkSet:
        """Returns a new record set with all DNSRecords of type 'A'."""
        return DNSLinkSet(
            {record for record in self if record.type == DNSRecordType.A})

    @property
    def PTR(self) -> DNSLinkSet:
        """Returns a new record set with all DNSRecords of type 'PTR'"""
        return DNSLinkSet(
            {record for record in self if record.type == DNSRecordType.PTR})

    @property
    def CNAME(self) -> DNSLinkSet:
        """Returns a new record set with all DNSRecords of type 'CNAME'"""
        return DNSLinkSet(
            {record for record in self if record.type == DNSRecordType.CNAME})

    # Record attributes

    @property
    def sources(self) -> set[str]:
        """Returns all sources in the set."""
        return {record.source for record in self}

    @property
    def destinations(self) -> set[DNSObject]:
        """Returns all destinations in the set."""
        return {record.destination for record in self}

    @property
    def names(self) -> set[str]:
        """Returns all destination names in the set."""
        return {record.destination.name for record in self}


class DNSObject(base.NetworkObject):
    """
    A NetworkObject representing an object in a managed DNS zone.
    """
    zone: Optional[str]
    """The DNS zone this object is from."""
    links: DNSLinkSet
    """A set of DNSLinks originating from this object."""
    implied_links: DNSLinkSet
    """A set of DNSLinks resolving to this object."""
    _node: Optional[Union[nodes.Node, nodes.NodeProxy]]
    """The node/proxy this DNSObject resolves to."""

    ## dunder methods

    def __init__(self, network: containers.Network, name: str, zone: str = None, labels: Iterable[str] = None) -> None:
        super().__init__(network, name, name, labels)
        self.zone = zone.lower() if zone else zone
        self.node = None
        self.links = DNSLinkSet()
        self.implied_links = DNSLinkSet()

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
        self.links.add(DNSLink(self, destination, source))
        destination.implied_links.add(DNSLink(destination, self, source))
        self.network.counter.inc_facet(CountedFacets.DNSLink)

    def to_psml(self) -> BeautifulSoup:
        soup = super().to_psml()
        header = soup.find('properties-fragment', id = 'header')
        header.append(Property(
            name = 'node',
            title = 'Node',
            value = XRef(docid = self.node.docid) if self.node else '—'
        ).tag)

        if isinstance(self.node, nodes.ProxiedNode):
            proxy_value: Union[str, XRef]
            if self.node.proxy.node:
                proxy_value = XRef(docid = self.node.proxy.node.docid)
            else:
                proxy_value = 'Not Provided'
            header.append(Property('proxy', proxy_value, 'Proxy').tag)
        
        soup.find('section', id = 'records').replace_with(self.links.to_psml().tag)
        soup.find('section', id = 'implied_records').replace_with(
            self.implied_links.difference(self.links).to_psml(implied = True).tag)

        return soup

    def merge(self, object: DNSObject) -> DNSObject: # type: ignore
        """
        In place merge of two DNSObjects of the same type.
        This method should always be called on the object entering the set.
        """
        if object.name == self.name:
            super().merge(object)
            self.links = self.links.union(object.links)
            self.implied_links = self.implied_links.union(object.implied_links)
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
        #TODO add updating the domains/ips attr on nodes
        # e.g. self._node.domains.remove(self.name) 
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
    txt_records: set[TXTRecord]
    """A set of TXT records in the zone of this domain."""
    caa_records: set[CAARecord]
    """A set of CAA records on this domain."""
    
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
            self.txt_records = set()
            self.caa_records = set()
            
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
        return (self.links.CNAME.names.union(self.implied_links.CNAME.names)).union(
            [self.name])

    @property
    def ips(self) -> set[str]:
        return self.links.A.names.union(self.implied_links.PTR.names)
    
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
            self.network.counter.inc_facet(CountedFacets.Domain)
        return self

    ## properties

    @property
    def subnets(self) -> set[str]:
        """Returns a set of IPv4 CIDR 8-bit subnets that this domain resolves to."""
        return {iptools.sort(ip) for ip in self.ips}

    ## methods

    def to_psml(self) -> BeautifulSoup:
        soup = super().to_psml()
        soup.find('section', id = 'txt_records').replace_with(
            Section('txt_records', 'TXT Records', [
                record.to_psml(f'{record.type}_record_{count}') 
                for count, record in enumerate(self.txt_records)
            ]).tag
        )
        soup.find('section', id = 'caa_records').replace_with(
            Section('caa_records', 'CAA Records', [
                record.to_psml(f'{record.type}_record_{count}') 
                for count, record in enumerate(self.caa_records)
            ]).tag
        )
        return soup

    @classmethod
    def from_psml(cls, network: containers.Network, psml: BeautifulSoup) -> Domain:
        assert psml.document['type'] == cls.type, f'Document type does not match "{cls.type}"'

        header = PropertiesFragment.from_tag(psml.find('properties-fragment', id = 'header')).to_dict()
        footer = Section.from_tag(psml.find('section', id = 'footer'))
        dns_records = Section.from_tag(psml.find('section', id = 'records'))
        
        domain = cls(network, header['name'], header['zone'], psml.find('labels').text.split(','))
        domain.psmlFooter = footer

        notes_section = psml.find('section', id='notes')
        if notes_section:
            notes_frag = notes_section.find('fragment', id='notes')
            if notes_frag:
                domain.notes = Fragment.from_tag(notes_frag)
        
        txt_records = psml.find('section', id = 'txt_records')
        if txt_records is not None:
            txts = set()
            for _txt in Section.from_tag(txt_records):
                txts.add(TXTRecord.from_psml(PropertiesFragment.from_tag(_txt.tag)))

        caa_records = psml.find('section', id = 'caa_records')
        if caa_records is not None:
            caas = set()
            for _caa in Section.from_tag(caa_records):
                caas.add(CAARecord.from_psml(PropertiesFragment.from_tag(_caa.tag)))

        for _record in dns_records:
            if _record.tag.name != 'properties-fragment':
                raise NameError(f'Section "dns_records" contains illegal element: {_record.tag.name}')
            record = PropertiesFragment.from_tag(_record.tag).to_dict()
            source: str = record.pop('source')
            xref: XRef = next(iter(record.values()))
            if not 'urititle' in xref.tag.attrs:
                raise AttributeError('Cannot instantiate Domain from PSML that has not been processed.')
            domain.link(xref.tag['urititle'], source)

        return domain

class IPv4Address(DNSObject):
    """
    A single IP address found in the network
    """
    subnet: str
    """The 24 bit CIDR subnet this IP is in."""
    is_private: bool
    """Whether or not this IP is private"""
    NAT: set[NATLink]
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
        return (self.links.CNAME.names.union(self.implied_links.CNAME.names)).union(
            [self.name])

    @property
    def domains(self) -> set[str]:
        return (self.links.PTR.names.union(self.implied_links.A.names))
    
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
        
        self.NAT.add(NATLink(self, destObj, source))
        destObj.NAT.add(NATLink(destObj, self, source))
        self.network.counter.inc_facet(CountedFacets.NATLink)

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
            self.network.counter.inc_facet(CountedFacets.IPv4)
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

    @classmethod
    def from_psml(cls, network: containers.Network, psml: BeautifulSoup) -> IPv4Address:
        # assert psml.document['type'] == cls.type, f'Document type does not match "{cls.type}"'

        header = PropertiesFragment.from_tag(psml.find('properties-fragment', id = 'header')).to_dict()
        footer = Section.from_tag(psml.find('section', id = 'footer'))
        dns_records = Section.from_tag(psml.find('section', id = 'records'))
        
        ipv4 = cls(network, header['name'], psml.find('labels').text.split(','))
        ipv4.psmlFooter = footer

        notes_section = psml.find('section', id='notes')
        if notes_section:
            notes_frag = notes_section.find('fragment', id='notes')
            if notes_frag:
                ipv4.notes = Fragment.from_tag(notes_frag)

        for _record in dns_records:
            if _record.tag.name != 'properties-fragment':
                raise NameError(f'Section "dns_records" contains illegal element: {_record.tag.name}')
            record = PropertiesFragment.from_tag(_record.tag).to_dict()
            source: str = record.pop('source')
            xref: XRef = next(iter(record.values()))
            if not 'urititle' in xref.tag.attrs:
                raise AttributeError('Cannot instantiate IPv4 from PSML that has not been processed.')
            ipv4.link(xref.tag['urititle'], source)

        return ipv4

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
            self.links.names or
            self.implied_links.names or
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

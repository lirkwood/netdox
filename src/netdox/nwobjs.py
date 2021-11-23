"""
This module contains the objects that directly represent an object in the network.
"""
from __future__ import annotations

import os
import re
from hashlib import sha256
from typing import TYPE_CHECKING, Iterable, Optional

from bs4 import BeautifulSoup, Tag
from netdox import base, helpers, iptools, utils
from netdox.psml import (DOMAIN_TEMPLATE, IPV4ADDRESS_TEMPLATE, NODE_TEMPLATE,
                         PropertiesFragment, Property, XRef, recordset2pfrags)

if TYPE_CHECKING:
    from netdox import Network

###########
# DNSObjs #
###########

class Domain(base.DNSObject):
    """
    A domain defined in a managed DNS zone.
    Contains all A/CNAME DNS records from managed zones using this domain as the record name.

    Subclasses DNSObject
    """
    subnets: set[str]
    """A set of the 24 bit CIDR subnets this domain resolves to."""
    TEMPLATE = DOMAIN_TEMPLATE
    
    ## dunder methods

    def __init__(self, 
            network: Network, 
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
        if re.fullmatch(utils.dns_name_pattern, name):
            super().__init__(
                network = network, 
                name = name, 
                zone = zone or '.'.join(name.split('.')[1:]), 
                labels = labels
            )
            
            self.records = {
                'A': helpers.RecordSet('A'),
                'CNAME': helpers.RecordSet('CNAME')
            }

            self.backrefs = {
                'CNAME': set(),
                'PTR': set()
            }

            self.subnets = set()
            
        else:
            raise ValueError('Must provide a valid name for a Domain (some FQDN)')
    
    ## abstract properties

    @property
    def docid(self) -> str:
        return '_nd_domain_' + self.identity.replace('.','_')

    @property
    def outpath(self) -> str:
        return os.path.normpath(os.path.join(utils.APPDIR, f'out/domains/{self.docid}.psml'))

    @property
    def domains(self) -> set[str]:
        return set(self.records['CNAME'].names + [self.name]).union(self.backrefs['CNAME'])

    @property
    def ips(self) -> set[str]:
        return set(self.records['A'].names).union(self.backrefs['PTR'])
    
    ## abstract methods

    def link(self, value: str, source: str) -> None:
        """
        Adds a DNS record from this domain to the provided destination.

        Adds a 2-tuple containing the destination and source to the relevant record set; self._cnames when destination is a FQDN, etc.

        :param value: The value for the DNS record, as a string.
        :type value: str
        :param source: The plugin that provided this link.
        :type source: str
        :raises ValueError: If the destination cannot be recognised as a FQDN or IPv4 address.
        """
        if iptools.valid_ip(value):
            self.records['A'].add(value, source)
            self.network.ips[value].backrefs['A'].add(self.name)
            if not iptools.public_ip(value):
                self.subnets.add(iptools.sort(value))

        elif re.fullmatch(utils.dns_name_pattern, value):
            self.records['CNAME'].add(value, source)
            self.network.domains[value].backrefs['CNAME'].add(self.name)

        else:
            raise ValueError('Unable to parse value as a domain or IPv4 address')

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

    def to_psml(self) -> BeautifulSoup:
        soup = super().to_psml()
        body = soup.find('section', id = 'records')

        for frag in recordset2pfrags(
            recordset = self.records['A'],
            id_prefix = 'A_record_',
            docid_prefix = '_nd_ip_',
            p_name = 'ipv4',
            p_title = 'A Record'
        ):  
            body.append(frag)

        for frag in recordset2pfrags(
            recordset = self.records['CNAME'],
            id_prefix = 'CNAME_record_',
            docid_prefix = '_nd_domain_',
            p_name = 'domain',
            p_title = 'CNAME Record'
        ):  
            body.append(frag)

        return soup

    def merge(self, domain: Domain) -> Domain: # type: ignore
        """
        In place merge of two Domain instances.
        This method should always be called on the object entering the set.

        :param domain: The Domain to merge with.
        :type domain: Domain
        :raises ValueError: If the Domain objects cannot be merged (if their name attributes are not equal).
        :return: This Domain object, which is now a superset of the two.
        :rtype: Domain
        """
        super().merge(domain)
        self.subnets |= domain.subnets
        return self

class IPv4Address(base.DNSObject):
    """
    A single IP address found in the network
    """
    nat: Optional[str]
    """The IP this address resolves to through the NAT."""
    subnet: str
    """The 24 bit CIDR subnet this IP is in."""
    is_private: bool
    """Whether or not this IP is private"""
    TEMPLATE = IPV4ADDRESS_TEMPLATE
    
    ## dunder methods

    def __init__(self, 
        network: Network, 
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

            self.records = {
                'PTR': helpers.RecordSet('PTR'),
                'CNAME': helpers.RecordSet('CNAME')
            }

            self.backrefs = {
                'A': set(),
                'CNAME': set()
            }

            self.subnet = self.subnetFromMask()
            self.nat = None
        else:
            raise ValueError('Must provide a valid name for an IPv4Address (some IPv4, in CIDR form)')

    ## abstract properties

    @property
    def docid(self) -> str:
        return '_nd_ip_' + self.identity.replace('.','_')

    @property
    def outpath(self) -> str:
        return os.path.normpath(os.path.join(utils.APPDIR, f'out/ips/{self.subnet.replace("/","_")}/{self.docid}.psml'))

    @property
    def domains(self) -> set[str]:
        return set(self.records['PTR'].names).union(self.backrefs['A'])

    @property
    def ips(self) -> set[str]:
        return set(self.records['CNAME'].names + [self.name]).union(self.backrefs['CNAME'])
    
    ## abstract methods

    def link(self, value: str, source: str) -> None:
        """
        Adds a record from this object to a DNSObject named *value*.
        Should also create a backref if the network attribute is set.

        :param value: The name of the DNSObject to link to.
        :type value: str
        :param source: The plugin that provided this link.
        :type source: str
        """
        if iptools.valid_ip(value):
            self.records['CNAME'].add(value, source)
            self.network.ips[value].backrefs['CNAME'].add(self.name)

        elif re.fullmatch(utils.dns_name_pattern, value):
            self.records['PTR'].add(value, source)
            self.network.domains[value].backrefs['PTR'].add(self.name)
            
        else:
            raise ValueError('Unable to parse value as a domain or IPv4 address')

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
        if self.unused:
            self.labels.add('unused')
        soup = super().to_psml()
        body = soup.find('section', id = 'records')

        for frag in recordset2pfrags(
            recordset = self.records['PTR'],
            id_prefix = 'PTR_record_',
            docid_prefix = '_nd_domain_',
            p_name = 'domain',
            p_title = 'PTR Record'
        ):  
            body.append(frag)

        # TODO convert NAT to recordset
        if self.nat:
            soup.find('properties-fragment', id = 'header').append(Property(
                name = 'nat',
                title = 'NAT Destination',
                value = XRef(docid = f'_nd_ip_{self.nat.replace(".","_")}')
            ))

        body.append(
            PropertiesFragment(id = 'implied_ptr', properties = [
                Property(
                        name = 'domain',
                        title = 'Implied PTR Record',
                        value = XRef(docid = f'_nd_domain_{domain.replace(".","_")}')
                    )
                for domain in self.backrefs['A']
                if domain not in self.records['PTR']
            ]))

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
        self.nat = ip.nat or self.nat
        return self

    ## properties

    @property
    def unused(self) -> bool:
        """
        Returns False if this object is pointing to any other objects, or is being pointed at.
        True otherwise.
        """
        return not bool(
            any([rs.names for rs in self.records.values()])
            or any(self.backrefs.values())
            or self.node
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


#########
# Nodes #
#########

class Node(base.NetworkObject):
    """
    A single physical or virtual machine.
    """
    identity: str
    """A string unique to this Node that can always be used to find it."""
    _domains: set[str]
    """A set of domains resolving to this Node."""
    _ips: set[str]
    """A set of IPv4 addresses resolving to this Node."""
    type: str = 'base'
    """A string unique to this implementation of Node."""
    _location: Optional[str]
    """Optional manual location attribute to use instead of the network locator."""
    TEMPLATE = NODE_TEMPLATE

    ## dunder methods

    def __init__(self, 
            network: Network, 
            name: str, 
            identity: str, 
            domains: Iterable[str], 
            ips: Iterable[str],
            labels: Iterable[str] = None
        ) -> None:
        self.identity = identity.lower()
        self.type = self.__class__.type
        self._location = None
        super().__init__(network, name, identity, labels)

        self._domains = {d.lower() for d in domains} if domains else set()
        self._ips = set(ips) if ips else set()

    ## abstract properties

    @property
    def psmlBody(self) -> list[Tag]:
        """
        Returns a list of section tags to add to the body of this Node's output PSML.

        :return: A list of ``<section />`` BeautifulSoup Tag objects.
        :rtype: list[Tag]
        """
        return []

    @property
    def docid(self) -> str:
        return (
            f'_nd_node_{self.__class__.type}_' +
            re.sub(utils.docid_invalid_patten, "_", self.identity)
        )

    @property
    def outpath(self) -> str:
        return os.path.normpath(os.path.join(utils.APPDIR, f'out/nodes/{self.docid}.psml'))

    @property
    def domains(self) -> set[str]:
        return self._domains

    @domains.setter
    def domains(self, val: set[str]) -> None:
        self._domains = val

    @property
    def ips(self) -> set[str]:
        return self._ips

    @ips.setter
    def ips(self, val: set[str]) -> None:
        self._ips = val

    ## abstract methods

    def _enter(self) -> Node:
        """
        Adds this Node to the network's NodeSet.

        :return: The identity of this Node.
        :rtype: str
        """
        if self.identity in self.network.nodes:
            self.network.nodes[self.identity] = self.merge(self.network.nodes[self.identity])
        else:
            self.network.nodes[self.identity] = self

        cache: set[str] = set()
        for domain in list(self.domains):
            cache |= self.network.nodes.resolveRefs(self.identity, domain, cache)

        for ip in list(self.ips):
            cache |= self.network.nodes.resolveRefs(self.identity, ip, cache)

        return self

    def to_psml(self) -> BeautifulSoup:
        soup = super().to_psml()

        body = soup.find('section', id = 'body')
        for tag in self.psmlBody:
            body.append(tag)
        body.unwrap()

        domains = PropertiesFragment('domains', properties = [
            Property(
                    name = 'domain',
                    title = 'Domain',
                    value = XRef(docid = f'_nd_domain_{domain.replace(".","_")}') \
                        if domain in self.network.domains else domain
                )
            for domain in self.domains
        ])

        ips = PropertiesFragment('ips', properties = [
            Property(
                    name = 'ipv4',
                    title = 'Public IP' if iptools.public_ip(ip) else 'Private IP',
                    value = XRef(docid = f'_nd_ip_{ip.replace(".","_")}') \
                        if ip in self.network.ips else ip
                )
            for ip in self.ips
        ])

        header = soup.find('section', id = 'header')
        header.append(domains)
        header.append(ips)

        return soup

    def merge(self, node: Node) -> Node: # type: ignore
        super().merge(node)
        self.domains |= node.domains
        self.ips |= node.ips
        return self

    ## properties

    @property
    def location(self) -> str:
        """
        Returns a location code based on the IPs associated with this node, and the configuration in ``locations.json``.

        :return: The location of this node
        :rtype: str
        """
        return self._location or self.network.locator.locate(self.ips) or '—'

    @location.setter
    def location(self, value: str) -> None:
        self._location = value

    @location.deleter
    def location(self) -> None:
        self._location = None


class DefaultNode(Node):
    """
    Default implementation of Node, with one private IPv4 address.
    """
    private_ip: str
    """The IP that this Node is using."""
    type = 'default'

    ## dunder methods

    def __init__(self, 
            network: Network,
            name: str, 
            private_ip: str,
            public_ips: Iterable[str] = [],
            domains: Iterable[str] = [],
            labels: Iterable[str] = None
        ) -> None:

        if iptools.valid_ip(private_ip) and not iptools.public_ip(private_ip):
            self.private_ip = private_ip
        else:
            raise ValueError(f'Invalid private IP: {private_ip}')

        super().__init__(
            network = network, 
            name = name,
            identity = private_ip,
            domains = domains,
            ips = [*public_ips] + [private_ip],
            labels = labels
        )


class PlaceholderNode(Node):
    """
    A placeholder Node intended to be consumed by another Node.
    If one of it's domains / ips get the node attribute set, 
    this object will be consumed by the new node and replaced in all locations.
    """
    type = 'placeholder'

    def __init__(self, 
            network: Network, 
            name: str, 
            domains: Iterable[str] = [], 
            ips: Iterable[str] = [],
            labels: Iterable[str] = None
        ) -> None:
        """
        Generates a random UUID to use for it's identity.
        If any of its domains / ips already have a node,
        it will create a ref from its own identity to that node, forcing a merge.
        If there are multiple unique nodes referenced by its DNSObjs, 
        an exception wil be raised.

        :param network: The network.
        :type network: Network
        :param name: Name for this node.
        :type name: str
        :param domains: A set of domains this node will listen on, defaults to []
        :type domains: Iterable[str], optional
        :param ips: A set of ips this node will listen on, defaults to []
        :type ips: Iterable[str], optional
        """

        hash = sha256(usedforsecurity = False)
        hash.update(bytes(name, 'utf-8'))
        hash.update(bytes(str(sorted(set(domains))), 'utf-8'))
        hash.update(bytes(str(sorted(set(ips))), 'utf-8'))

        super().__init__(
            network = network, 
            name = name, 
            identity = hash.hexdigest(), 
            domains = domains, 
            ips = ips,
            labels = labels
        )

        nodes: set[Node] = set()
        for domain in self.domains:
            node = self.network.domains[domain].node
            if node: nodes.add(node)
        for ip in self.ips:
            node = self.network.ips[ip].node
            if node: nodes.add(node)
            
        assert len(nodes) <= 1, 'Placeholder cannot be consumed by more than one node.'
        if nodes:
            self.network.nodes.addRef(nodes.pop(), self.identity)

    ## abstract properties

    @property
    def psmlBody(self) -> list[Tag]:
        """
        Returns an Iterable containing section tags to add to the body of this Node's output PSML.

        :return: A set of ``<section />`` BeautifulSoup tags.
        :rtype: Iterable[Tag]
        """
        return []

    ## properties

    @property
    def aliases(self) -> set[str]:
        """
        Returns all the refs to this node in the containing NodeSet.
        This is useful for guaranteeing this objects removal after consumption.

        :return: A set of refs to this node.
        :rtype: set[str]
        """
        return {ref for ref, node in self.network.nodes.nodes.items() if node is self}

    ## methods

    def _enter(self) -> Node:
        super()._enter()
        return self.network.nodes[self.identity]

    def merge(self, node: Node) -> Node: # type: ignore
        """
        Copies any data in this object to the corresponding attributes in *node*.
        Replaces *self* in all locations with *node*.

        :param node: The Node to merge replace *self* with.
        :type node: Node
        :return: The *node* argument.
        :rtype: Node
        """
        node.domains |= self.domains
        node.ips |= self.ips
        node.psmlFooter += self.psmlFooter

        for domain in self.domains:
            if self.network.domains[domain].node is self:
                self.network.domains[domain].node = node

        for ip in self.ips:
            if self.network.ips[ip].node is self:
                self.network.ips[ip].node = node

        for alias in self.aliases:
            self.network.nodes[alias] = node

        return node

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Iterator, Type

import iptools
from bs4 import Tag

from .base import NetworkObject, NetworkObjectContainer

if TYPE_CHECKING:
    from . import Network
    from .base import NetworkObject, NetworkObjectContainer
    from .ips import IPv4Address

class Node(NetworkObject):
    """
    A Node on the network representing one machine/VM/Kubelet/etc.
    Name should be the FQDN of the machine unless it has a non-default type.
    """
    private_ip: str
    """The IP that this Node is using."""
    public_ips: set
    """A set of public IPs that this Node uses."""
    domains: set
    """A set of domains that are hosted on this Node."""
    type: str
    """The type of this Node."""

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

        self.psmlFooter = []

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

    @property
    def psmlBody(self) -> Iterable[Tag]:
        """
        Returns an Iterable containing section tags to add to the body of this Node's output PSML.

        :return: A set of ``<section />`` BeautifulSoup tags.
        :rtype: Iterable[Tag]
        """
        return []

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

    @classmethod
    def from_dict(cls: Type[Node], string: str) -> Node:
        """
        Instantiates a Node from its __dict__ attribute.

        :param constructor: The dictionary to use.
        :type constructor: dict
        :return: A instance of this class.
        :rtype: Node
        """
        instance = super(Node, cls).from_dict(string)
        instance.public_ips = set(instance.public_ips)
        instance.domains = set(instance.domains)
        return instance


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

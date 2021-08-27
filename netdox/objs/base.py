"""
This module contains the abstract base classes for most of the other classes in the objs package.
"""
from __future__ import annotations

import os
from abc import ABC, ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Iterable, Iterator, Type, Union

from bs4 import Tag

from netdox.utils import APPDIR

if TYPE_CHECKING:
    from netdox.objs import Network, helpers

###########
# Objects #
###########

class NetworkObjectMeta(ABCMeta):
    """
    Metaclass for an object belonging to a Network.
    Adds itself to the provided network object *after* instantiation.
    """

    def __call__(cls, *args, **kwargs) -> NetworkObject:
        """
        Calls the `_add` method on *network* after `__init__`, 
        allowing the network to override attributes set during initialisation.

        :param network: The network.
        :type network: Network
        :return: An instance of this class.
        :rtype: NetworkObject
        """
        nwobj = super().__call__(*args, **kwargs)
        nwobj.network._add(nwobj)
        return nwobj

class NetworkObject(metaclass=NetworkObjectMeta):
    """
    Base class for an object in the network.
    """
    name: str
    """The name to give this object."""
    docid: str
    """A unique, predictable identifier to be used for docid and filename in PageSeeder."""
    network: Network
    """The containing network."""
    psmlFooter: list[Tag] = None
    """A list of fragment tags to add to the *footer* section of this object's output PSML."""

    ## dunder methods

    def __init__(self, network: Network, name: str, docid: str) -> None:
        """
        Sets the instances attributes to the values provided, and adds itself to *network*.

        :param network: The network to add this object to.
        :type network: Network
        :param name: The name to give this object in PageSeeder.
        :type name: str
        :param docid: The docid / filename to give this object's document in PageSeeder.
        :type docid: str
        """
        self.network = network
        self.name = name.lower().strip()
        self.docid = docid.lower()

        self.psmlFooter = []

    ## properties

    @property
    @abstractmethod
    def outpath(self) -> str:
        """
        The absolute filepath to write this NetworkObject document to.

        :return: An absolute filepath.
        :rtype: str
        """ 
        pass
    
    ## methods

    def merge(self, object: NetworkObject) -> NetworkObject:
        """
        Should add the contents of any containers in *object* to the corresponding containers in *self*.

        Used to resolve identity conflicts in containers.
        This method should always be called on the object entering the set.
        """
        self.psmlFooter += object.psmlFooter
        return self

class DNSObject(NetworkObject):
    """
    A NetworkObject representing an object in a managed DNS zone.
    """
    zone: str
    """The DNS zone this object is from."""
    records: dict[str, helpers.RecordSet]
    """A dictionary mapping record type to a RecordSet."""
    backrefs: dict[str, set]
    """Like records but stores reverse references from DNSObjects linking to this one."""
    node: Node
    """The node this DNSObject resolves to"""

    ## dunder methods

    def __init__(self, network: Network, name: str, docid: str, zone: str) -> None:
        super().__init__(network, name, docid)
        self.zone = zone.lower() if zone else zone
        self.node = None

    ## properties

    @property
    @abstractmethod
    def domains(self) -> set[str]:
        """
        Returns a set of all the domains this DNSObject has a record / backref to.

        :return: A set of domains relevant to this object, as strings.
        :rtype: set[str]
        """
        ...

    @property
    @abstractmethod
    def ips(self) -> set[str]:
        """
        Returns a set of all the ips this DNSObject has a record / backref to.

        :return: A set of ips relevant to this object, as strings.
        :rtype: set[str]
        """
        ...

    ## methods

    @abstractmethod
    def link(self, value: str, source: str) -> None:
        """
        Adds a record from this object to a DNSObject named *value*.
        Should also create a backref if there is a network.

        :param value: The name of the DNSObject to link to.
        :type value: str
        :param source: The plugin that provided this link.
        :type source: str
        """
        pass

    def merge(self, object: DNSObject) -> DNSObject:
        """
        In place merge of two DNSObjects of the same type.
        This method should always be called on the object entering the set.
        """
        super().merge(object)
        for recordType in self.records:
            if recordType in object.records:
                self.records[recordType] |= object.records[recordType]

        for recordType in self.backrefs:
            if recordType in object.backrefs:
                self.backrefs[recordType] |= object.backrefs[recordType]

        return self

class Node(NetworkObject):
    """
    A single physical or virtual machine.
    """
    identity: str
    """A string unique to this Node that can always be used to find it."""
    domains: set[str]
    """A set of domains resolving to this Node."""
    ips: set[str]
    """A set of IPv4 addresses resolving to this Node."""
    type: str = None
    """A string unique to this implementation of Node."""
    _location: str = None
    """Optional manual location attribute to use instead of the network locator."""

    ## dunder methods

    def __init__(self, 
            network: Network, 
            name: str, 
            docid: str,
            identity: str, 
            domains: Iterable[str], 
            ips: Iterable[str]
        ) -> None:
        self.identity = identity.lower()
        self.type = self.__class__.type
        super().__init__(network, name, docid)

        self.domains = {d.lower() for d in domains} if domains else set()
        self.ips = set(ips) if ips else set()

    ## abstract properties

    @property
    @abstractmethod
    def psmlBody(self) -> list[Tag]:
        """
        Returns a list of section tags to add to the body of this Node's output PSML.

        :return: A list of ``<section />`` BeautifulSoup Tag objects.
        :rtype: list[Tag]
        """
        pass

    @property
    def outpath(self) -> str:
        return os.path.normpath(os.path.join(APPDIR, f'out/nodes/{self.docid}.psml'))

    ## abstract methods

    def merge(self, node: Node) -> Node:
        super().merge(node)
        self.domains |= node.domains
        self.ips |= node.ips
        self.location = self.network.locator.locate
        return self

    ## properties

    @property
    def location(self) -> str:
        """
        Returns a location code based on the IPs associated with this node, and the configuration in `locations.json`.

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


##############
# Containers #
##############

class NetworkObjectContainer(ABC):
    """
    Container for a set of network objects
    """
    objectType: str
    """The type of NetworkObject this object can contain."""
    objectClass: Type[NetworkObject]
    """The class of objectType."""
    objects: dict
    """A dictionary of the NetworkObjects in this container."""
    network: Network
    """The network this container is in, if any."""

    ## dunder methods

    def __getitem__(self, key: str) -> NetworkObject:
        return self.objects[key.lower()]

    def __setitem__(self, key: str, value: NetworkObject) -> None:
        self.objects[key.lower()] = value

    def __delitem__(self, key: str) -> None:
        del self.objects[key.lower()]

    def __iter__(self) -> Iterator[NetworkObject]:
        yield from set(self.objects.values())

    def __contains__(self, key: str) -> bool:
        return self.objects.__contains__(key.lower())

    ## methods

    @abstractmethod
    def _add(self, object: NetworkObject) -> None:
        """
        Add a single NetworkObject to the set, merge if an object with that name is already present.

        :param object: The NetworkObject to add to the set.
        :type object: NetworkObject
        """
        pass

class DNSObjectContainer(NetworkObjectContainer):
    """
    Container for a set of DNSObjects.
    """

    ## dunder methods

    def __init__(self, network: Network, objects: Iterable[DNSObject] = []) -> None:
        self.network = network
        self.objects = {object.name: object for object in objects}

    def __contains__(self, key: Union[str, DNSObject]) -> bool:
        if isinstance(key, str):
            return super().__contains__(key)
        else:
            return super().__contains__(key.name)

    ## abstract methods

    def _add(self, object: DNSObject) -> None:
        if object.name in self:
            self[object.name] = object.merge(self[object.name])
        else:
            self[object.name] = object

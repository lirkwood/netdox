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
    from netdox.objs.nwobjs import Node

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
        Calls the ``_add`` method on *network* after ``__init__``, 
        allowing the network to override attributes set during initialisation.

        :param network: The network.
        :type network: Network
        :return: An instance of this class.
        :rtype: NetworkObject
        """
        nwobj = super().__call__(*args, **kwargs)
        return nwobj._enter()


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
    labels: set[str]
    """A set of labels to apply to this object's output document."""

    ## dunder methods

    def __init__(self, network: Network, name: str, docid: str, labels: Iterable[str] = None) -> None:
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
        
        self.labels = set(labels) if labels else set()
        self.labels.add('show-reversexrefs')

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

    @abstractmethod
    def _enter(self) -> None:
        """
        Adds this object to the network and NetworkObjectContainer.
        This function is called after instantiation, 
        and its value is returned by ``NetworkObjectMeta.__call__``.
        """
        pass

    def merge(self, object: NetworkObject) -> NetworkObject:
        """
        Should add the contents of any containers in *object* to the corresponding containers in *self*.

        Used to resolve identity conflicts in containers.
        This method should always be called on the object entering the set.
        """
        self.psmlFooter += object.psmlFooter
        self.labels |= object.labels
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

    def __init__(self, network: Network, name: str, docid: str, zone: str, labels: Iterable[str] = None) -> None:
        super().__init__(network, name, docid, labels)
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
        if object.name == self.name:
            super().merge(object)
            for recordType in self.records:
                if recordType in object.records:
                    self.records[recordType] |= object.records[recordType]

            for recordType in self.backrefs:
                if recordType in object.backrefs:
                    self.backrefs[recordType] |= object.backrefs[recordType]

            return self
        else:
            raise AttributeError('Cannot merge DNSObjects with different names.')


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

class DNSObjectContainer(NetworkObjectContainer):
    """
    Container for a set of DNSObjects.
    """
    objectClass: Type[DNSObject]

    ## dunder methods

    def __init__(self, network: Network, objects: Iterable[DNSObject] = []) -> None:
        self.network = network
        self.objects = {object.name: object for object in objects}

    def __getitem__(self, key: str) -> DNSObject:
        if key not in self.objects:
            self.objects[key] = self.objectClass(self.network, key)
        return super().__getitem__(key)

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

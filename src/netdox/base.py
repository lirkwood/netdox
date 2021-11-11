"""
This module contains the abstract base classes for most of the other classes in the objs package.
"""
from __future__ import annotations

from abc import ABC, ABCMeta, abstractmethod
from functools import cache
from typing import (TYPE_CHECKING, Generic, Iterable, Iterator, Optional, Type,
                    TypeVar, Union)

from bs4.element import Tag

if TYPE_CHECKING:
    from netdox import Network, helpers
    from netdox.nwobjs import Node

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
    identity: str
    """A unique, predictable identifier to be used for retrieving objects from NWObjContainers"""
    network: Network
    """The containing network."""
    psmlFooter: list[Tag]
    """A list of fragment tags to add to the *footer* section of this object's output PSML."""
    labels: set[str]
    """A set of labels to apply to this object's output document."""
    DEFAULT_LABELS = ['show-reversexrefs', 'netdox-default']

    ## dunder methods

    def __init__(self, network: Network, name: str, identity: str, labels: Iterable[str] = None) -> None:
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
        self.identity = identity.lower()

        self.psmlFooter = []
        
        self.labels = self.network.labels[self.docid]
        self.labels.update(self.DEFAULT_LABELS)
        if labels: self.labels |= set(labels)

    ## properties

    @property
    @abstractmethod
    def docid(self) -> str:
        """
        Should return the identity of this object, 
        with some additional consistent name mangling to reduce collisions.

        :return: A string that is valid as a PageSeeder docid.
        :rtype: str
        """
        pass

    @property
    @abstractmethod
    def outpath(self) -> str:
        """
        The absolute filepath to write this NetworkObject document to.
        Filename be composed of the docid + file extension.

        :return: An absolute filepath.
        :rtype: str
        """ 
        pass

    @property
    @abstractmethod
    def domains(self) -> set[str]:
        """
        Returns a set of all the domains this NetworkObject has resolves to/from.

        :return: A set of FQDNs.
        :rtype: set[str]
        """
        ...

    @property
    @abstractmethod
    def ips(self) -> set[str]:
        """
        Returns a set of all the ips this NetworkObject has resolves to/from.

        :return: A set of IPv4Addresses.
        :rtype: set[str]
        """
        ...
    
    ## methods

    @abstractmethod
    def _enter(self) -> NetworkObject:
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

    @cache
    def getAttr(self, attr: str) -> Union[str, None]:
        """
        Returns the value of *attr* for the first label on this object that it is configured on.

        **Note:** Attributes from labels that are configured higher in the config file take 
        precedence over those underneath.

        :param attr: Attribute value to return.
        :type attr: str
        :return: The single unique value, or None.
        :rtype: Union[str, None]
        """
        for label in self.network.config.labels:
            if label in self.labels:
                val = self.network.config.labels[label][attr]
                if val: return val
        return None

NWObjT = TypeVar('NWObjT', bound = NetworkObject)

class DNSObject(NetworkObject):
    """
    A NetworkObject representing an object in a managed DNS zone.
    """
    zone: Optional[str]
    """The DNS zone this object is from."""
    records: dict[str, helpers.RecordSet]
    """A dictionary mapping record type to a RecordSet."""
    backrefs: dict[str, set]
    """Like records but stores reverse references from DNSObjects linking to this one."""
    node: Optional[Node]
    """The node this DNSObject resolves to"""

    ## dunder methods

    def __init__(self, network: Network, name: str, zone: str = None, labels: Iterable[str] = None) -> None:
        super().__init__(network, name, name, labels)
        self.zone = zone.lower() if zone else zone
        self.node = None

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

    def merge(self, object: DNSObject) -> DNSObject: # type: ignore
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

    #TODO add exclusion validation at this level: _enter?

DNSObjT = TypeVar('DNSObjT', bound = DNSObject)

##############
# Containers #
##############

class NetworkObjectContainer(ABC, Generic[NWObjT]):
    """
    Container for a set of network objects
    """
    objectType: str
    """The type of NetworkObject this object can contain."""
    objectClass: Type[NWObjT]
    """The class of objectType."""
    objects: dict[str, NWObjT]
    """A dictionary of the NetworkObjects in this container."""
    network: Network
    """The network this container is in, if any."""

    ## dunder methods

    def __getitem__(self, key: str) -> NWObjT:
        return self.objects[key.lower()]

    def __setitem__(self, key: str, value: NWObjT) -> None:
        self.objects[key.lower()] = value

    def __delitem__(self, key: str) -> None:
        del self.objects[key.lower()]

    def __iter__(self) -> Iterator[NWObjT]:
        yield from set(self.objects.values())

    def __contains__(self, key: str) -> bool:
        return self.objects.__contains__(key.lower())

class DNSObjectContainer(NetworkObjectContainer[DNSObjT], Generic[DNSObjT]):
    """
    Container for a set of DNSObjects.
    """

    ## dunder methods

    def __init__(self, network: Network, objects: Iterable[DNSObjT] = []) -> None:
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

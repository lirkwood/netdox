from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Iterator, Type

from bs4 import Tag

if TYPE_CHECKING:
    from . import Network
    from .objects import Node

###########
# Objects #
###########

class NetworkObject(ABC):
    """
    Base class for an object in the network.
    """
    name: str
    """The name to give this object."""
    docid: str
    """A unique, predictable identifier to be used for docid and filename in PageSeeder."""
    _network: Network = None
    """The internal reference to the containing Network object if there is one."""
    container: NetworkObjectContainer = None
    """The containing NetworkObjectContainer if there is one."""
    subnets: set
    """A set of private subnets this object resolves to."""
    psmlFooter: list[Tag] = None
    """A list of fragment tags to add to the *footer* section of this object's output PSML."""

    ## properties

    @property
    def network(self) -> Network:
        """
        Return the current Network container.

        :return: The current Network
        :rtype: Network
        """
        return self._network

    @network.setter
    @abstractmethod
    def network(self, new_network: Network):
        """
        Set the internal network attribute to new_network.
        Should also trigger any link resolution etc. that must be done upon entering a network.

        :param new_network: The network this NetworkObject has been added to.
        :type new_network: Network
        """
        self._network = new_network
        self.location = new_network.locator.locate(self)

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
    def merge(self, object: NetworkObject) -> NetworkObject:
        """
        In place merge of two NetworkObject instances of the same type.
        Must return self.
        This method should always be called on the object entering the set.
        """
        return self

    def to_dict(self) -> dict:
        """
        Returns a JSON-safe dictionary, that can be passed to ``from_dict``.

        :return: A dictionary describing this class.
        :rtype: dict
        """
        return self.__dict__ | {'_network': None, 'container': None, 'psmlFooter': [str(tag) for tag in self.psmlFooter]}


class RecordSet:
    """Container for DNS records"""
    _records: set
    """Set of 2-tuples containing a record value and the plugin name that provided it."""

    ## dunder methods

    def __init__(self) -> None:
        self._records = set()

    def __iter__(self) -> Iterator[str]:
        yield from self.records

    ## properties

    @property
    def records(self) -> list[str]:
        """
        Returns a list of the record values in this set

        :return: A list record values as strings
        :rtype: list[str]
        """
        return [value for value, _ in self._records]
    
    ## methods

    def add(self, value: str, source: str) -> None:
        self._records.add((value.lower().strip(), source))

class DNSObject(NetworkObject):
    """
    A NetworkObject representing an object in a managed DNS zone.
    """
    zone: str
    """The DNS zone this object is from."""
    records: dict[str, RecordSet]
    """A dictionary mapping record type to a RecordSet."""
    backrefs: dict[str, set]
    """Like records but stores reverse references from DNSObjects linking to this one."""
    node: Node
    """The node this DNSObject resolves to"""

    ## methods

    @abstractmethod
    def link(self, value: str, source: str) -> None:
        """
        Adds a record from this object to a DNSObject named *value*.

        :param value: The name of the DNSObject to link to.
        :type value: str
        :param source: The plugin that provided this link.
        :type source: str
        """
        pass


class Node(NetworkObject):
    """
    A single physical or virtual machine.
    """
    identity: str
    """A string unique to this Node that can always be used to find it."""
    location: str = None
    """The location as it appears in ``locations.json``, assigned based on IP address by *Locator*."""
    domains: set[str]
    """A set of domains resolving to this Node."""
    ips: set[str]
    """A set of IPv4 addresses resolving to this Node."""
    type: str
    """A string unique to this implementation of Node."""

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
        return os.path.abspath(f'out/nodes/{self.docid}.psml')


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

    def __init__(self, objectSet: list[NetworkObject] = [], network: Network = None) -> None:
        self.objects = {object.name: object for object in objectSet}
        self.network = network

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

    def to_json(self, path: str) -> None:
        """
        Serialises the set of NetworkObjects to a JSON file using the JSONEncoder defined in this file.
        """
        with open(path, 'w') as stream:
            stream.write(json.dumps({
                'objectType': self.objectType,
                'objects': [object.to_dict() for object in self]
            }, indent = 2, cls = JSONEncoder))

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

    def replace(self, identifier: str, replacement: NetworkObject) -> None:
        """
        Replace the object with the specified identifier with a new object.

        Calls merge on the replacement with the target object passed as the argument,
        then mutates the original object into the superset, preserving its identity.
        Also adds a ref under the replacement's name in ``self.objects``.

        If target object is not in the set, the new object is simply added as-is, 
        and *identifier* will point to it.

        :param identifier: The string to use to identify the existing object to replace.
        :type identifier: str
        :param object: The object to replace the existing object with.
        :type object: NetworkObject
        """
        if identifier in self:
            original = self[identifier]
            superset = replacement.merge(original)
            original.__class__ = superset.__class__
            for key, val in superset.__dict__.items():
                original.__dict__[key] = val
            self[replacement.name] = original
        else:
            self.add(replacement)


######################
# Helper JSONEncoder #
######################

class JSONEncoder(json.JSONEncoder):
    """
    JSON Encoder compatible with sets and datetime objects
    """
    def default(self, obj):
        """
        :meta private:
        """
        if isinstance(obj, set):
            return sorted(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return super().default(obj)

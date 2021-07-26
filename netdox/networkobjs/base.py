from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Iterator, Type

from bs4 import BeautifulSoup, Tag

if TYPE_CHECKING:
    from . import Network

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
    location: str = None
    """The location as it appears in ``locations.json``, assigned based on IP address by *Locator*."""
    psmlFooter: list[Tag] = None
    """A list of BeautifulSoup objects (must be valid children of ``section``) to add to the *footer* section of this object's output PSML."""

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

    @classmethod
    def from_dict(cls: Type[NetworkObject], constructor: dict) -> NetworkObject:
        """
        Instantiates this class from its __dict__ attribute.

        :param constructor: The dictionary to use.
        :type constructor: dict
        :return: A instance of this class.
        :rtype: NetworkObject
        """
        instance = cls(constructor['name'])
        instance.__dict__.update(constructor)
        instance.psmlFooter = [BeautifulSoup(tag, features = 'xml') for tag in instance.psmlFooter]
        return instance


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

    def __init__(self, objectSet: list[NetworkObject] = [], network: Network = None) -> None:
        self.objects = {object.name: object for object in objectSet}
        self.network = network

    def __getitem__(self, key: str) -> NetworkObject:
        return self.objects[key]

    def __setitem__(self, key: str, value: NetworkObject) -> None:
        self.objects[key] = value

    def __delitem__(self, key: str) -> None:
        del self.objects[key]

    def __iter__(self) -> Iterator[NetworkObject]:
        yield from self.objects.values()

    def __contains__(self, key: str) -> bool:
        return self.objects.__contains__(key)

    @classmethod
    def from_dict(cls, constructor: dict) -> NetworkObjectContainer:
        """
        Instantiates a NetworkObjectContainer from a dictionary of attributes.

        :param constructor: A dictionary of the instances attributes.
        :type constructor: dict
        :return: An instance of this class.
        :rtype: NetworkObjectContainer
        """
        if constructor['objectType'] == cls.objectType:
            return cls([cls.objectClass.from_dict(object) for object in constructor['objects']])
        else:
            raise ValueError(f'Cannot instantiate {type(cls)._name__} from dictionary of {constructor["objectType"]}')

    @classmethod
    def from_json(cls, path: str) -> NetworkObjectContainer:
        """
        Instantiates this class from a JSON file.
        Expects a string the same as that returned by *to_json*.

        :param path: The JSON file to read.
        :type path: str
        :return: A instance of this class.
        :rtype: NetworkObjectContainer
        """
        with open(path, 'r') as stream:
            return cls.from_dict(json.loads(stream.read()))

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

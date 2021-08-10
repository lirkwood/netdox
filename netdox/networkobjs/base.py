from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable, TYPE_CHECKING, Iterator, Type, Union

from bs4 import Tag

if TYPE_CHECKING:
    from . import Network

###########
# Objects #
###########

class NetworkObject(ABC):
    """
    Base class for an object in the network.
    Adds itself to *network* upon instantiation.
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
        self.network._add(self)

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

    def to_dict(self) -> dict:
        """
        Returns a JSON-safe dictionary to be used for serialisation / data exploration.

        :return: A dictionary describing this class' attributes.
        :rtype: dict
        """
        return self.__dict__ | {'network': None, 'psmlFooter': [str(tag) for tag in self.psmlFooter]}


class RecordSet:
    """Container for DNS records"""
    _records: set
    """Set of 2-tuples containing a record value and the plugin name that provided it."""

    ## dunder methods

    def __init__(self) -> None:
        self._records = set()

    def __iter__(self) -> Iterator[str]:
        yield from self.records

    def __ior__(self, recordset: RecordSet) -> RecordSet:
        return self._records.__ior__(recordset._records)

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

    def items(self) -> Iterator[tuple[str, str]]:
        yield from self._records

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

    ## dunder methods

    def __init__(self, network: Network, name: str, docid: str, zone: str) -> None:
        super().__init__(network, name, docid)
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

    def to_dict(self) -> dict:
        return super().to_dict() | {'node': None}

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
    location: str = None
    """The location as it appears in ``locations.json``, assigned based on IP address by *Locator*."""
    type: str
    """A string unique to this implementation of Node."""

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
        super().__init__(network, name, docid)

        self.domains = set(domains) if domains else set()
        self.ips = set(ips) if ips else set()
        self.location = self.network.locator.locate(self.ips)

        for domain in self.domains:
            if domain in self.network.domains and not self.network.domains[domain].node:
                self.network.domains[domain].node = self

        for ip in self.ips:
            if ip in self.network.domains and not self.network.ips[ip].node:
                self.network.ips[ip].node = self

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

    ## abstract methods

    def merge(self, node: Node) -> Node:
        super().merge(node)
        self.domains |= node.domains
        self.ips |= node.ips
        self.location = self.network.locator.locate
        return self


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

    def to_json(self, path: str) -> None:
        """
        Serialises the set of NetworkObjects to a JSON file using the JSONEncoder defined in this file.
        """
        with open(path, 'w') as stream:
            stream.write(json.dumps({
                'objectType': self.objectType,
                'objects': [object.to_dict() for object in self]
            }, indent = 2, cls = JSONEncoder))

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
        elif isinstance(obj, RecordSet):
            return obj._records
        else:
            return super().default(obj)

"""
This module contains the abstract base classes for most of the other classes in the objs package.
"""
from __future__ import annotations
import logging

import os
import re
import copy
from abc import ABC, ABCMeta, abstractmethod
from functools import lru_cache
from typing import (TYPE_CHECKING, Generic, Iterable, Iterator, Optional, Type,
                    TypeVar, Union)

from bs4 import BeautifulSoup
from xml.sax.saxutils import escape
from netdox import psml

if TYPE_CHECKING:
    from netdox import Network
    
logger = logging.getLogger(__name__)

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
    psmlFooter: psml.Section
    """A PSML section to be inserted at the footer of the document."""
    labels: set[str]
    """A set of labels to apply to this object's output document."""
    DEFAULT_LABELS = ['show-reversexrefs', 'netdox-default']
    """A set of labels to apply to this object upon instantiation."""
    _notes: psml.Fragment
    """A string of content that is editable on the remote server."""
    DEFAULT_NOTES = '<fragment id="notes"><para>—</para></fragment>'
    """String form of the default notes content."""
    type: str
    """A string unique to each subclass of NetworkObject."""
    TEMPLATE: str
    """The template to populate during serialisation."""
    _organization: Optional[str]
    """A fallback value for the organization of this object."""

    ## dunder methods

    def __init__(self, 
        network: Network, 
        name: str, 
        identity: str, 
        labels: Iterable[str] = None, 
        notes: psml.Fragment = None
    ) -> None:
        """
        Sets the instances attributes to the values provided, and adds itself to *network*.

        :param network: The network to add this object to.
        :type network: Network
        :param name: The name to give this object in PageSeeder.
        :type name: str
        :param docid: The docid / filename to give this object's document in PageSeeder.
        :type docid: str
        """
        if not hasattr(self, 'TEMPLATE') or not self.TEMPLATE:
            raise AttributeError('NetworkObject must have the TEMPLATE attribute set.')

        self.network = network
        self.name = name.lower().strip()
        self.identity = identity.lower()
        self._organization = None
        
        self.psmlFooter = psml.Section('footer', fragments = [
            psml.PropertiesFragment(id = 'search', properties = [
                psml.Property(
                    name = 'terms', 
                    title = 'Search Terms', 
                    value = self.search_terms
            )], attrs = {'labels':'s-hide-content'})
        ])
        
        self.labels = self.network.labels[self.docid]
        self.labels.update(self.DEFAULT_LABELS)
        if labels: self.labels |= set(labels)
        self.notes = notes or psml.Fragment.from_tag(
            BeautifulSoup(self.DEFAULT_NOTES, 'xml').fragment)

    def __str__(self) -> str:
        cls = self.__class__
        return f'<{cls.__module__}.{cls.__name__} {self.identity}>'

    def __repr__(self) -> str:
        return str(self)

    ## properties

    @property
    def organization(self) -> Optional[str]:
        """
        Returns the URIID of the organization document this object belongs to,
        if any.

        Will return the first organization that shares a label with this object,
        or the fallback value if no orgs match.

        Assigning a value to this property will set the fallback value.

        :return: An integer (as a string), or None.
        :rtype: str
        """
        for uri, labels in self.network.config.organizations.items():
            if (self.labels & labels):
                return uri
        return self._organization

    @organization.setter
    def organization(self, value: str) -> None:
        """
        Sets the fallback value for this object's organization.

        :param value: The URIID of an organization document.
        :type value: str
        """
        self._organization = value

    @organization.deleter
    def organization(self) -> None:
        self._organization = None

    @property
    def search_terms(self) -> list[str]:
        """
        A set of terms this object should be searchable by.

        :return: A list of strings.
        :rtype: list[str]
        """
        tokenized = self.name.split('.')
        return ['.'.join(tokenized[i + 1:]) for i in range(len(tokenized) - 1)]

    @property
    def notes(self) -> psml.Fragment:
        """
        The notes that have been written for this object, escaped for XML.

        :return: A string that is safe as XML text.
        :rtype: str
        """
        return self._notes

    @notes.setter
    def notes(self, val: psml.Fragment) -> None:
        assert isinstance(val, psml.Fragment), f'Set notes to "{str(val)}"'
        self._notes = val

    @notes.deleter
    def notes(self) -> None:
        self._notes = psml.Fragment.from_tag(
            BeautifulSoup(self.DEFAULT_NOTES, 'xml').fragment)

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

    def to_psml(self) -> BeautifulSoup:
        """
        Serialises this object to PSML and returns a BeautifulSoup object.
        """
        if len(self.docid) > 100:
            raise AttributeError(
                'Cannot serialise object with docid longer than 100 chars.')
            #TODO add creating dummy document with explanation if this exc is raised
        body = copy.copy(self.TEMPLATE)
        for field in re.findall(r'(#![a-zA-Z0-9_]+)', self.TEMPLATE):
            attr = getattr(self, field.replace('#!',''), None)
            if attr:
                if not isinstance(attr, str):
                    try:
                        attr = str(attr)
                    except Exception:
                        continue
                body = re.sub(field, attr, body)
            else:
                body = re.sub(field, '—', body)

        soup = BeautifulSoup(body, features = 'xml')
        soup.find('labels').string = ','.join(self.labels)
        soup.find('section', id = 'footer').replace_with(self.psmlFooter.tag)
        soup.find('section', id = 'notes').append(self.notes.tag)
        
        if self.organization: 
            soup.find(attrs={'name':'org'}).append(psml.XRef(self.organization).tag)
        else:
            org_prop = soup.find(attrs={'name':'org'})
            org_prop['datatype'] = 'string'
            org_prop['value'] = '—'

        return soup

    @abstractmethod
    def from_psml(self, network: Network, psml: BeautifulSoup):
        """
        Instantiates an object from its psml representation.

        :param network: The network to create this object inside of.
        :type network: Network
        :param psml: The PSML object this object was serialised to initially.
        :type psml: BeautifulSoup
        """
        ...

    def serialise(self) -> None:
        """
        Serialises this object to PSML and writes it to the outpath.
        """
        os.makedirs(os.path.dirname(self.outpath), exist_ok = True)
        try:
            outsoup = self.to_psml()
        except Exception as exc:
            logger.error(f"NWObj {self.identity} failed to write to psml: {exc}")
        else:
            with open(self.outpath, 'w', encoding = 'utf-8') as stream:
                stream.write(str(outsoup))

    def merge(self, object: NetworkObject) -> NetworkObject:
        """
        Should add the contents of any containers in *object* to the corresponding containers in *self*.

        Used to resolve identity conflicts in containers.
        This method should always be called on the object entering the set.
        """
        self.psmlFooter.extend(object.psmlFooter)
        self.labels |= object.labels

        if str(self.notes) == self.DEFAULT_NOTES:
            self.notes = psml.Fragment.from_tag(copy.copy(object.notes.tag))

        return self

    @lru_cache(maxsize = None)
    def getAttr(self, attr: str) -> Union[str, None]: # TODO rename get_attr
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
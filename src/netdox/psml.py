"""
Provides some useful classes, functions and constants for generating and manipulating PSML using BeautifulSoup4.
"""

from __future__ import annotations
from abc import ABC, abstractmethod

from collections import defaultdict
from typing import Any, Iterable, Iterator, Mapping, Optional, Union
from copy import copy

from bs4.element import Tag, PageElement

###########
# Classes #
###########

class PSMLElement(ABC):
    tag: Tag
    """This PSMLElement as a BeautifulSoup Tag"""

    def __str__(self) -> str:
        return str(self.tag)

    def __eq__(self, other) -> bool:
        return str(self) == str(other)
    
    @classmethod
    @abstractmethod
    def from_tag(cls, tag: Tag) -> PSMLElement:
        """
        Instantiates a PSMLElement from a BeautifulSoup Tag.

        :param tag: The Tag to read data from.
        :type tag: Tag
        :return: A PSMLElement.
        :rtype: PSMLElement
        """
        ...

class Section(PSMLElement):
    """
    PSML Section element.
    """
    _indices: dict[str, int]
    """IDs of the fragments in this section, mapped to their index."""
    _frags: dict[str, PSMLFragment]
    """IDs of the fragments in this section, mapped to the PSMLFragment object."""

    def __init__(self, 
            id: str, 
            title: str = None, 
            fragments: Iterable[PSMLFragment] = None,
            attrs: Mapping[str, Any] = None
        ) -> None:
        """
        Default constructor.

        :param id: ID unique within the document
        :type id: str
        :param title: Optional title to display at top of section, defaults to None
        :type title: str, optional
        """
        attrs = dict(attrs) if attrs else {}
        if title: attrs['title'] = title
        self.tag = Tag(
            name = 'section',
            is_xml = True,
            can_be_empty_element = True,
            attrs = {'id': id} | attrs
        )

        self._indices = {}
        self._frags = {}
        for fragment in (fragments or ()):
            self.insert(fragment)

    def __str__(self) -> str:
        return str(self.tag)

    def __eq__(self, other) -> bool:
        return str(self) == str(other)

    def __iter__(self) -> Iterator[PSMLFragment]:
        yield from self._frags.values()

    def get(self, fragment_id: str) -> PSMLFragment:
        """
        Gets a fragment with the given id.

        :param fragment_id: The ID of the fragment to return.
        :type fragment_id: str
        :return: The specified fragment object.
        :rtype: PSMLFragment
        """
        return self._frags[fragment_id]

    def insert(self, fragment: PSMLFragment, index: int = None) -> None:
        """
        Inserts a new fragment at the specified index.
        If a fragment with an equal ID is already present, 
        the new fragment will replace it.

        :param fragment: Fragment to insert into the section.
        :type fragment: Fragment
        :param index: Index to insert fragment at.
        Defaults to index of fragment with the same ID, or last.
        :type index: int, optional
        """
        if fragment.id in self._indices:
            index = index or self._indices.get(fragment.id)
            self.tag.find(attrs = {'id': fragment.id}, recursive = False).decompose()

        index = index or len(self._indices)
        self._frags[fragment.id] = fragment
        self._indices[fragment.id] = index
        self.tag.insert(index, copy(fragment.tag))

    def extend(self, fragments: Iterable[PSMLFragment]):
        """
        Inserts each fragment in *fragments* into this section.

        :param fragments: Some fragments to add to this section.
        :type fragments: Iterable[Fragment]
        """
        for frag in fragments: self.insert(frag)

    @classmethod
    def from_tag(cls, tag: Tag) -> Section:
        """
        Instantiates a Section from a BeautifulSoup Tag.

        :param tag: A valid PSML Section element as a BS4 Tag.
        :type tag: Tag
        :raises AttributeError: If the Tag is missing the 'id' attribute.
        :return: A Section object.
        :rtype: Section
        """
        if not tag.has_attr('id'):
            raise AttributeError('Section tag missing required attribute \'id\'')
        frags = []
        for frag_tag in tag.find_all(True, recursive = False):
            frag = fragment_from_tag(frag_tag)
            if frag is not None: frags.append(frag)

        return cls(
            id = tag['id'],
            title = tag['title'] if tag.has_attr('title') else None,
            fragments = frags,
            attrs = tag.attrs
        )

class PSMLFragment(PSMLElement):
    """
    Parent class for the various fragments in PSML.
    """

    @classmethod
    @abstractmethod
    def from_tag(cls, tag: Tag) -> PSMLFragment:
        ...
    
    @property
    def id(self) -> str:
        """
        Returns the value of the ID attribute of this PSMLFragment.
        """
        return self.tag.attrs['id']

    def insert(self, element: PageElement, index: Optional[int] = None) -> None:
        """
        Inserts a Tag into the PSMLFragment at the given index (or the end),
        only if it is valid content.

        :param element: Tag to insert.
        :type element: Tag
        :param index: Index to insert the Tag at, defaults to last.
        :type index: int, optional
        """
        if index:
            self.tag.insert(index, element)
        else:
            self.tag.append(element)

    def extend(self, elements: Iterable[PageElement]) -> None:
        for elem in elements: self.insert(elem)


class Fragment(PSMLFragment):
    tag: Tag
    """This Fragment as a BeautifulSoup Tag."""

    def __init__(self, 
            id: str, 
            elements: Iterable[PageElement] = None,
            attrs: Mapping[str, Any] = None) -> None:
        """
        Default constructor.

        :param id: ID unique within the document.
        :type id: str
        :param attrs: A map of attributes, defaults to None
        :type attrs: Mapping[str, Any], optional
        """
        attrs = dict(attrs) if attrs else {}
        self.tag = Tag(
            name = 'fragment',
            is_xml = True,
            can_be_empty_element = True,
            attrs = {'id': id} | attrs
        )

        self.extend(elements or ())

    @classmethod
    def from_tag(cls, tag: Tag) -> Fragment:
        """       
        Instantiates a Fragment from a BeautifulSoup Tag.

        :param tag: A valid PSML Fragment element as a BS4 Tag.
        :type tag: Tag
        :raises AttributeError: If the Tag is missing the 'id' attribute.
        :return: A Fragment object.
        :rtype: Fragment
        """
        if not tag.has_attr('id'):
            raise AttributeError('Fragment tag missing required attribute \'id\'')
        return cls(tag['id'], tag.contents, tag.attrs)
    
def image_fragment(id: str, path: str) -> Fragment:
    """ Creates a fragment containing a image located at the given path."""
    para = Tag(name = 'para', is_xml = True)
    para.append(Tag(name = 'image', is_xml = True, attrs = {'src': path}))
    return Fragment(id, [para])

class PropertiesFragment(PSMLFragment):
    """
    PSML PropertiesFragment element.
    """
    properties: list[Property]
    """List of Property objects."""

    def __init__(self, 
            id: str, 
            properties: Iterable[Property] = None,
            attrs: Mapping[str, Any] = None,
        ) -> None:
        """
        Default constructor.

        :param id: ID unique within the document.
        :type id: str
        :param properties: Some properties to immediately append to this element, 
        defaults to []
        :type properties: Iterable[Property], optional
        :param attrs: A map of attributes, defaults to None
        :type attrs: Mapping[str, Any], optional
        """
        attrs = dict(attrs) if attrs else {}
        self.tag = Tag(
            name = 'properties-fragment',
            is_xml = True,
            can_be_empty_element = True,
            attrs = {'id': id} | attrs
        )

        self.properties = []
        self.extend(properties or ())

    ## abstract methods

    def insert(self, property: Property, index: Optional[int] = None) -> None:
        if index is None:
            self.tag.append(property.tag)
            self.properties.append(property)
        else:
            self.tag.insert(index, property.tag)
            self.properties.insert(index, property)

    def extend(self, elements: Iterable[Property]) -> None:
        for elem in elements:
            self.insert(elem)

    @classmethod
    def from_tag(cls, fragment: Tag) -> PropertiesFragment:
        properties = []
        for property in fragment('property'):
            properties.append(Property.from_tag(property))
        return cls(fragment['id'], properties)

    ## methods 

    def get(self, property_name: str) -> Optional[Property]:
        """
        Gets a property from its name.
        None if no property with that name.

        :param property_name: Name of the property to return.
        :type property_name: str
        :return: The property in this fragment with the given name, or None.
        :rtype: Optional[Property]
        """
        for property in self.properties:
            if property.name == property_name:
                return property
        return None

    def to_dict(self) -> dict:
        """
        Returns a dictionary of child properties names mapped to values.

        :return: A dictionary of strings mapped to strings, Links, or lists of either.
        :rtype: dict
        """
        outdict = defaultdict(list)
        for property in self.properties:
            outdict[property.tag.attrs['name']].append(property.value)
        return {key: val[0] if len(val) == 1 else val for key, val in outdict.items()}

    @classmethod
    def from_dict(cls, id: str, constructor: dict) -> PropertiesFragment:
        """
        Constructs a PropertiesFragment from a dictionary of property names,
        mapped to strings, Links, or lists of either.

        :param constructor: Constructor dict.
        :type constructor: dict
        :raises TypeError: If the value is of an unrecognised type.
        :return: A PropertiesFragment instance.
        :rtype: PropertiesFragment
        """
        pfrag = cls(id)
        for key, value in constructor.items():
            if isinstance(value, str) or not isinstance(value, Iterable):
                pfrag.insert(Property(key, value))

            elif isinstance(value, Iterable):
                for _value in value:
                    pfrag.insert(Property(key, _value))
            
            else:
                raise TypeError(
                    'Could not instantiate a Property from a value of: '+ str(value))
        return pfrag

class MediaFragment(PSMLFragment):

    def __init__(self, 
        id: str, 
        attrs: Mapping[str, Any] = None, 
        mediatype: str = None, 
        content: PageElement = None
    ) -> None:
        attrs = dict(attrs) if attrs else {}
        if mediatype is not None:
            attrs['mediatype'] = mediatype
            
        self.tag = Tag(
            name = 'media-fragment',
            is_xml = True,
            can_be_empty_element = True,
            attrs = {'id': id} | attrs
        )
        
        if content is not None:
            self.insert(content)

    @classmethod
    def from_tag(cls, fragment: Tag) -> MediaFragment:
        if len(fragment.contents) == 1:
            return cls(fragment['id'], fragment.attrs, fragment.contents[0])
        else:
            return cls(fragment['id'], fragment.attrs)

FRAGMENT_NAMES: dict[str, type[PSMLFragment]] = {
    'fragment': Fragment, 'properties-fragment': PropertiesFragment, 'media-fragment': MediaFragment
}
"""Maps the tag name of fragment types to their respective classes."""

def fragment_from_tag(tag: Tag) -> Optional[PSMLFragment]:
    """
    Creates a psml Fragment object (or one of it's subclasses) 
    from a BeautifulSoup tag.

    :param tag: A BS4 Tag
    :type tag: Tag
    :return: A Fragment, or None if *tag* is not a valid PSML fragment.
    :rtype: Optional[Fragment]
    """
    name = tag.name
    if name in FRAGMENT_NAMES:
        return FRAGMENT_NAMES[name].from_tag(tag)
    return None

class Property(PSMLElement):
    """
    PSML Property element.
    """
    name: str
    """Name of this property."""
    title: Optional[str]
    """Title of this property"""
    datatype: Optional[str]
    """Datatype of this property. Defaults to string."""
    value: Union[PSMLLink, Iterable[str], str, None]
    """Value of this property."""

    def __init__(self, 
        name: str,
        value: Union[PSMLLink, Iterable[str], str, None] = None,
        title: Optional[str] = None,
        datatype: Optional[str] = None,
        attrs: Mapping[str, Any] = {}
    ) -> None:
        """
        Constructor.

        :param name: Value for the name attribute.
        :type name: str
        :param value: Value for the value attribute, can be a string or a Link tag.
        :type value: str, optional
        :param title: Value for the title attribute. Defaults to name.
        :type title: str
        """
        _attrs = {'name': name, 'title': title or name}
        if datatype is not None and datatype != 'string':
            _attrs['datatype'] = datatype
        
        self.tag = Tag(
            name = 'property', 
            is_xml = True, 
            can_be_empty_element = True, 
            attrs = _attrs | attrs
        )
        
        self.name = name
        self.title = title
        self.value = value
        self.datatype = datatype
        if value:
            if isinstance(value, str):
                self.tag.attrs['value'] = value
            elif isinstance(value, PSMLLink):
                self.tag.attrs['datatype'] = value.tag.name
                self.tag.append(value.tag)
            elif isinstance(value, Iterable) and value:
                self.tag.attrs['multiple'] = 'true'
                for val in value:
                    val_tag = Tag(name = 'value')
                    val_tag.string = str(val)
                    self.tag.append(val_tag)

    @classmethod
    def from_tag(cls, property: Tag) -> Property:
        assert 'name' in property.attrs, 'Property missing name attribute.'
        name = str(property['name'])
        title = str(property['title']) if 'title' in property.attrs else None
        
        if property.has_attr('value'):
            return cls(
                name,
                property['value'], 
                title, 
                attrs = property.attrs
            )
        
        elif any(True for _ in property.children): # hack to check emptiness of iterator
            if property.has_attr('datatype') and property['datatype'] in PROPERTY_DATATYPES:
                child = property.find(property['datatype'])
                if child is not None:
                    return cls(
                        name,
                        PROPERTY_DATATYPES[property['datatype']].from_tag(child),
                        title,
                        str(property['datatype']),
                        property.attrs
                    )
                else:
                    return cls(
                        name,
                        None,
                        title,
                        str(property['datatype']),
                        property.attrs
                    )
                
            elif property.has_attr('multiple'):
                return cls(
                    name,
                    [val.string for val in property('value')], 
                    title,
                    attrs = property.attrs
                )

            else:
                raise NotImplementedError(
                    'Failed to parse property from the following tag: '+ str(property))

        else:
            return cls(name)


class PSMLLink(PSMLElement):
    """
    Represents a link tag in PSML.
    These elements will always have a separate closing tag due to the string content logic.
    """

    @classmethod
    @abstractmethod
    def from_tag(cls, tag: Tag) -> PSMLLink:
        ...

class XRef(PSMLLink):
    """
    Represents an XRef element.
    """

    def __init__(self, 
        uriid: str = None, 
        docid: str = None, 
        href: str = None, 
        frag = 'default',
        attrs: Mapping[str, Any] = None,
        string: str = None
    ) -> None:
        """
        Constructor.
        Provide one or more of URIID, docid, or href.
        The first one that is set will be used.

        :param uriid: URIID of the document to link to, defaults to None
        :type uriid: str, optional
        :param docid: docid of the document to link to, defaults to None
        :type docid: str, optional
        :param href: path to the document to link to, defaults to None
        :type href: str, optional
        :param frag: Fragment to link to, defaults to 'default'
        :type frag: str, optional
        :param attrs: Additional attributes to set.
        :type attrs: Mapping[str, Any], optional
        :param string: String content for the element, defaults to nothing 
        (will be populated by PageSeeder if not set).
        :type string: str, optional
        """
        if uriid or docid or href:
            self.tag = Tag(
                name = 'xref',
                is_xml = True,
                can_be_empty_element = True,
                attrs = (attrs or {}) | {'frag': frag}
            )
            if string is not None:
                self.tag.string = string
            if uriid:
                self.tag.attrs['uriid'] = uriid
            if docid:
                self.tag.attrs['docid'] = docid
            if href:
                self.tag.attrs['href'] = href
        else:
            raise AttributeError("One of 'uriid', 'docid', or 'href' must be set.")

    @classmethod
    def from_tag(cls, tag: Tag) -> XRef:
        return cls(
            tag['uriid'] if tag.has_attr('uriid') else None,
            tag['docid'] if tag.has_attr('docid') else None,
            tag['href'] if tag.has_attr('href') else None,
            attrs = tag.attrs, 
            string = tag.string
        )

class Link(PSMLLink):
    """
    Represents a Link element.
    """

    def __init__(self, 
        url: str, 
        attrs: Mapping[str, Any] = None, 
        string: str = None
    ) -> None:
        """
        Constructor.

        :param url: URL to link to.
        :type url: str
        :param attrs: Additional attributes to set.
        :type attrs: Mapping[str, Any]
        :param string: String content for the element, defaults to the link value.
        :type string: str, optional
        """
        self.tag = Tag(
            name = 'link', 
            is_xml = True,
            can_be_empty_element = True,
            attrs = (attrs or {}) | {'href': url}, 
        )
        self.tag.string = url if string is None else string

    @classmethod
    def from_tag(cls, tag: Tag) -> Link:
        return cls(
            tag['href'],
            attrs = tag.attrs,
            string = tag.string
        )

PROPERTY_DATATYPES: dict[str, type[PSMLLink]] = {
    'xref': XRef, 'link': Link
}
"""Maps Property value datatypes (e.g. 'xref') to their respective classes."""


#############
# Templates #
#############

DOMAIN_TEMPLATE = '''
    <document type="domain" level="portable" xmlns:t="http://pageseeder.com/psml/template">

        <documentinfo>
            <uri docid="#!docid" title="#!name">
                <labels />
            </uri>
        </documentinfo>

        <metadata>
            <properties>
                <property name="template_version"     title="Template version"   value="6.6" />
            </properties>
        </metadata>

        <section id="title" lockstructure="true">
            <fragment id="title">
                <heading level="1">
                    <link href="https://#!name">#!name</link>
                </heading>                    
            </fragment>
        </section>
        
        <section id="header" lockstructure="true">

            <properties-fragment id="header">
                <property name="name"       title="Name"            value="#!name" />
                <property name="zone"       title="DNS Zone"        value="#!zone" />
                <property name="org"        title="Organization"    datatype="xref" />
            </properties-fragment>

        </section>

        <section id="records" title="DNS Records" fragmenttype="a_record,cname_record" />

        <section id="implied_records" title="Implied DNS Records" lockstructure="true" />

        <section id="caa_records" title="CAA Records" fragmenttype="caa_record" />

        <section id="txt_records" title="TXT Records" fragmenttype="txt_record" />
        
        <section id="footer" />

        <section id="notes" />

    </document>
'''

IPV4ADDRESS_TEMPLATE = '''
    <document type="ip" level="portable" xmlns:t="http://pageseeder.com/psml/template">

        <documentinfo>
            <uri docid="#!docid" title="#!name">
                <labels />
            </uri>
        </documentinfo>

        <metadata>
            <properties>
                <property name="template_version"     title="Template version"   value="3.5" />
            </properties>
        </metadata>

        <section id="title" lockstructure="true">
            <fragment id="title">
                <heading level="1">#!name</heading>
            </fragment>
        </section>

        <section id="header" lockstructure="true">
        
            <properties-fragment id="header">
                <property name="name"               title="Name"                  value="#!name" /> 
                <property name="subnet"             title="Subnet"              value="#!subnet" />
                <property name="org"                title="Organization"        datatype="xref" />
            </properties-fragment>

        </section>
        
        <section id="records" title="DNS Records" fragmenttype="ptr_record,cname_record,nat_entry" />

        <section id="implied_records" title="Implied DNS Records" lockstructure="true" />
        
        <section id="footer" />

        <section id="notes" />

    </document>
'''

NODE_TEMPLATE = '''
    <document type="node" level="portable" xmlns:t="http://pageseeder.com/psml/template">

        <documentinfo>
            <uri docid="#!docid" title="#!name">
                <labels />
            </uri>
        </documentinfo>

        <metadata>
            <properties>
                <property name="template_version"     title="Template version"   value="1.3" />
            </properties>
        </metadata>

        <section id="title">
            <fragment id="title">
                <heading level="1">#!name</heading>                    
            </fragment>
        </section>
        
        <section id="header">

            <properties-fragment id="header">
                <property name="name"       title="Name"            value="#!name" />
                <property name="identity"   title="Identity"        value="#!identity" />
                <property name="type"       title="Node Type"       value="#!type" />
                <property name="location"   title="Location"        value="#!location" />
                <property name="org"        title="Organization"    datatype="xref" />
            </properties-fragment>

        </section>

        <section id="body" />

        <section id="footer" />

        <section id="notes" overwrite="false" />

    </document>
'''

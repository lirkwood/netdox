"""
Provides some useful classes, functions and constants for generating and manipulating PSML using BeautifulSoup4.
"""

from __future__ import annotations
from abc import ABC, abstractmethod

from collections import defaultdict
from typing import Any, Iterable, Iterator, Mapping, Union

from bs4.element import Tag

###########
# Classes #
###########

class Section:
    """
    PSML Section element.
    """
    _tag: Tag
    """The internal tag object for this section."""
    _frags: dict[str, int]
    """IDs of the fragments in this section, mapped to their index."""

    def __init__(self, 
            id: str, 
            title: str = None, 
            fragments: Iterable[Fragment] = None,
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
        self._tag = Tag(
            name = 'section',
            is_xml = True,
            can_be_empty_element = True,
            attrs = {'id': id} | attrs
        )

        self._frags = {}
        for fragment in (fragments or ()):
            self.insert(fragment)

    def __str__(self) -> str:
        return str(self._tag)

    def __eq__(self, other) -> bool:
        return str(self) == str(other)

    def __iter__(self) -> Iterator[Fragment]:
        yield from self._tag.find_all(True, recursive = False)

    def insert(self, fragment: Fragment, index: int = None) -> None:
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
        if fragment.id in self._frags:
            index = index or self._frags.get(fragment.id)
            self._tag.find(attrs = {'id': fragment.id}, recursive = False).decompose()

        index = index or len(self._frags)
        self._frags[fragment.id] = index
        self._tag.insert(index, fragment)

    def extend(self, fragments: Iterable[Fragment]):
        """
        Inserts each fragment in *fragments* into this section.

        :param fragments: Some fragments to add to this section.
        :type fragments: Iterable[Fragment]
        """
        for frag in fragments: self.insert(frag)

class Fragment(Tag):

    def __init__(self, id: str, attrs: Mapping[str, Any] = None) -> None:
        """
        Default constructor.

        :param id: ID unique within the document.
        :type id: str
        :param attrs: A map of attributes, defaults to None
        :type attrs: Mapping[str, Any], optional
        """
        attrs = dict(attrs) if attrs else {}
        super().__init__(
            name = 'fragment',
            is_xml = True,
            can_be_empty_element = True,
            attrs = {'id': id} | attrs
        )
    
    @property
    def id(self) -> str:
        return self.attrs['id']

class PropertiesFragment(Fragment):
    """
    PSML PropertiesFragment element.
    """

    def __init__(self, 
            id: str, 
            properties: Iterable[Property] = [],
            attrs: Mapping[str, Any] = None,
        ) -> None:
        """
        Default constructor.

        :param id: ID unique within the document.
        :type id: str
        :param properties: Some properties to immediately append to this element, defaults to []
        :type properties: Iterable[Property], optional
        :param attrs: A map of attributes, defaults to None
        :type attrs: Mapping[str, Any], optional
        """
        super().__init__(id, attrs)
        self.name = 'properties-fragment'

        for property in properties:
            self.append(property)

    @property
    def id(self) -> str:
        return self['id']

    @property
    def properties(self) -> Iterable[Property]:
        return self('property')

    def to_dict(self) -> dict:
        """
        Returns a dictionary of child properties names mapped to values.

        :return: A dictionary of strings mapped to strings, Links, or lists of either.
        :rtype: dict
        """
        outdict = defaultdict(list)
        for property in self.children:
            outdict[property.attrs['name']].append(property.value)
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
                pfrag.append(Property(key, value))

            elif isinstance(value, Iterable):
                for _value in value:
                    pfrag.append(Property(key, _value))
            
            else:
                raise TypeError(
                    'Could not instantiate a Property from a value of: '+ str(value))
        return pfrag

    @classmethod
    def from_tag(cls, fragment: Tag) -> PropertiesFragment:
        properties = []
        for property in fragment('property'):
            properties.append(Property.from_tag(property))
        return cls(fragment['id'], properties)


class Property(Tag):
    """
    PSML Property element.
    """

    def __init__(self, 
        name: str,
        value: Union[PSMLLink, Iterable[str], str],
        title: str = None,
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
        
        super().__init__(
            name = 'property', 
            is_xml = True, 
            can_be_empty_element = True, 
            attrs = _attrs | attrs
        )
        
        self.value = value
        if value:
            if isinstance(value, str):
                self.attrs['value'] = value
            elif isinstance(value, PSMLLink):
                self.attrs['datatype'] = value.name
                self.append(value)
            elif isinstance(value, Iterable) and value:
                self.attrs['multiple'] = 'true'
                for val in value:
                    val_tag = Tag(name = 'value')
                    val_tag.string = str(val)
                    self.append(val_tag)
        else:
            self.attrs['value'] = ''

    @classmethod
    def from_tag(cls, property: Tag):
        title = property['title'] if 'title' in property.attrs else None
        if property.has_attr('value'):
            return cls(
                property['name'], 
                property['value'], 
                title, 
                property.attrs
            )
        
        elif property.children:
            if property.has_attr('datatype') and property['datatype'] in PROPERTY_DATATYPES:
                return cls(
                    property['name'], 
                    PROPERTY_DATATYPES[property['datatype']].from_tag(
                        property.findChild()
                    ),
                    title,
                    property.attrs
                )
            elif property.has_attr('multiple'):
                return cls(
                    property['name'], 
                    [val.string for val in property('value')], 
                    title,
                    property.attrs
                )

            else:
                raise NotImplementedError(
                    'Failed to parse property from the following tag: '+ str(property))

        elif property.has_attr('name'):
            return cls(property['name'], '')

        else:
            raise AttributeError(
                'Cannot create Property from tag with no value, children, or name.')


class PSMLLink(Tag, ABC):
    """
    Represents a link tag in PSML.
    These elements will always have a separate closing tag due to the string content logic.
    """

    def __init__(self, name: str, value: str, attrs: dict, string: str = None):
        """
        Constructor.

        :param name: The name of the element / datatype.
        :type name: str
        :param value: Value for the link.
        :type value: str
        :param attrs: Additional attributes to set.
        :type attrs: dict
        :param string: String content for the element, defaults to the link value.
        :type string: str, optional
        """
        super().__init__(
            name = name,
            is_xml = True, 
            can_be_empty_element = True,
            attrs = attrs
        )
        self.string = string if string is not None else value

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
            super().__init__(
                name = 'xref',
                value = uriid or docid or href, # type: ignore
                attrs = (attrs or {}) | {'frag': frag},
                string = string or ''
            )
            if uriid:
                self.attrs['uriid'] = uriid
            if docid:
                self.attrs['docid'] = docid
            if href:
                self.attrs['href'] = href
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
        super().__init__(
            name = 'link', 
            value = url, 
            attrs = (attrs or {}) | {'href': url}, 
            string = string
        )

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
                <property name="template_version"     title="Template version"   value="6.4" />
            </properties>
        </metadata>

        <section id="title" lockstructure="true">
            <fragment id="title">
                <heading level="2">Domain name</heading>
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

        <section id="footer" />

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
                <property name="template_version"     title="Template version"   value="3.4" />
            </properties>
        </metadata>

        <section id="title" lockstructure="true">
            <fragment id="title">
                <heading level="2">IP Address</heading>
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
                <property name="template_version"     title="Template version"   value="1.2" />
            </properties>
        </metadata>

        <section id="title">
            <fragment id="title">
                <heading level="2">Node</heading>
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

    </document>
'''

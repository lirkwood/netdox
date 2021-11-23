"""
Provides some useful classes, functions and constants for generating and manipulating PSML using BeautifulSoup4.
"""

from __future__ import annotations
from abc import ABC, abstractmethod

from collections import defaultdict
from typing import TYPE_CHECKING, Any, Iterable, Mapping, Union

from bs4.element import Tag

if TYPE_CHECKING:
    from netdox.helpers import RecordSet

###########
# Classes #
###########

class PropertiesFragment(Tag):
    """
    PSML PropertiesFragment element.
    """

    def __init__(self, 
            id: str, 
            properties: Iterable[Property] = [],
            attrs: Mapping[str, Any] = {},
        ) -> None:
        """
        Default constructor.

        :param id: ID unique within the document
        :type id: str
        :param properties: Some properties to immediately append to this element, defaults to []
        :type properties: Iterable[Property], optional
        :param attrs: A map of attributes, defaults to {}
        :type attrs: Mapping[str, Any], optional
        """

        super().__init__(
            name = 'properties-fragment', 
            is_xml = True, 
            can_be_empty_element = True, 
            attrs = {'id': id} | attrs
        )

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
        value: Union[PSMLLink, str],
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
            return cls(
                property['name'], 
                PROPERTY_DATATYPES[property['datatype']].from_tag(
                    property.findChild()
                ),
                title,
                property.attrs
            )

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
# Functions #
#############


def recordset2pfrags(
        recordset: RecordSet, 
        id_prefix: str, 
        docid_prefix: str, 
        p_name: str, 
        p_title: str
    ) -> list[Tag]:
    """
    Generates properties-fragments for the DNS records in *recordset* and returns them.

    Iterates over a set of 2-tuples, containing a record destination and the source plugin.
    Generate a properties-fragment for each tuple, with an xref to the destination and a property holding the source plugin.
    Appends each properties-fragment to the current ``self.body``.

    :param recordset: An Iterable object containing 2-tuples each describing a DNS record.
    :type recordset: Iterable[Tuple[str, str]]
    :param id_prefix: The prefix to give each properties-fragment.
    :type id_prefix: str
    :param docid_prefix: The prefix to give each xref *docid* attribute.
    :type docid_prefix: str
    :param p_name: The name to give each xref property.
    :type p_name: str
    :param p_title: The title to give each xref property.
    :type p_title: str
    """
    frags = []
    count = 0
    for value, plugin in recordset.items():
        frags.append(PropertiesFragment(id = id_prefix + str(count), properties = [
            Property(
                name = p_name, 
                title = p_title, 
                value = XRef(docid = docid_prefix + value.replace(".","_"))
            ),
            Property(
                name = 'source', 
                title = 'Source Plugin', 
                value = plugin
            )
        ]))
        count += 1
    return frags


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
                <property name="template_version"     title="Template version"   value="6.2" />
            </properties>
        </metadata>

        <section id="title">
            <fragment id="title">
                <heading level="2">Domain name</heading>
                <heading level="1">
                    <link href="https://#!name">#!name</link>
                </heading>                    
            </fragment>
        </section>
        
        <section id="header">

            <properties-fragment id="header">
                <property name="name"       title="Name"        value="#!name" />
                <property name="zone"       title="DNS Zone"    value="#!zone" />
            </properties-fragment>

        </section>

        <section id="records" title="DNS Records" fragmenttype="record" />

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
                <property name="template_version"     title="Template version"   value="3.2" />
            </properties>
        </metadata>

        <section id="title">
            <fragment id="title">
                <heading level="2">IP Address</heading>
                <heading level="1">#!name</heading>
            </fragment>
        </section>

        <section id="header">
        
            <properties-fragment id="header">
                <property name="ipv4"               title="IP"                  value="#!name" /> 
                <property name="subnet"             title="Subnet"              value="#!subnet" />
            </properties-fragment>

        </section>
        
        <section id="records" title="DNS Records" fragmenttype="record" />
        
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
                <property name="template_version"     title="Template version"   value="1.1" />
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
                <property name="name" title="Name" value="#!name" />
                <property name="identity" title="Identity" value="#!identity" />
                <property name="type" title="Node Type" value="#!type" />
                <property name="location" title="Location" value="#!location" />
            </properties-fragment>

        </section>

        <section id="body" />

        <section id="footer" />

    </document>
'''

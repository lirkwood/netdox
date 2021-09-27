"""
Provides some useful functions and constants for generating and manipulating PSML using BeautifulSoup4.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Iterable, Mapping, Union

from bs4 import BeautifulSoup, Tag

if TYPE_CHECKING:
    from objs.base import NetworkObject
    from objs.helpers import RecordSet

###########
# Classes #
###########

class PropertiesFragment(Tag):
    """
    PSML PropertiesFragment element.
    """
    id: str
    """ID unique within the document"""
    properties: Iterable[Property]
    """Some properties to immediately append to this element."""

    def __init__(self, 
            id: str, 
            namespace: str = None, 
            prefix: str = None, 
            attrs: Mapping[str, Any] = {},
            properties: Iterable[Property] = []
        ) -> None:

        self.id = id
        super().__init__(
            name = 'properties-fragment', 
            is_xml = True, 
            can_be_empty_element = True, 
            namespace = namespace, 
            prefix = prefix, 
            attrs = {'id': id} | attrs
        )

        for property in properties:
            self.append(property)

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
        
        if isinstance(value, str):
            self.attrs['value'] = value
        else:
            self.attrs['datatype'] = value.name
            self.append(value)


class PSMLLink(Tag):
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
        super().__init__(
            name = 'xref',
            value = uriid or docid or href,
            attrs = (attrs or {}) | {'frag': frag},
            string = string or ''
        )
        if uriid:
            self.attrs['uriid'] = uriid
        elif docid:
            self.attrs['docid'] = docid
        elif href:
            self.attrs['href'] = href
        else:
            raise AttributeError("One of 'uriid', 'docid', or 'href' must be set.")

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


#############
# Functions #
#############

def populate(template: str, nwobj: NetworkObject) -> BeautifulSoup:
    """
    Populates a NetworkObject template with the attributes from *nwobj*.

    :param template: The template to populate.
    :type template: str
    :param nwobj: The object to copy the attribute from.
    :type nwobj: NetworkObject
    :return: A /BeautifulSoup object containing the populated and parsed template.
    :rtype: BeautifulSoup
    """
    template = re.sub('#!docid', nwobj.docid, template)
    for attribute, value in nwobj.__dict__.items():
        if isinstance(value, str):
            template = re.sub(f'#!{attribute}', value, template)
        elif value is None:
            template = re.sub(f'#!{attribute}', '—', template)
    soup = BeautifulSoup(template, features = 'xml')
    return soup

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


def pfrag2dict(fragment: str) -> dict:
    """
    Converts a PSML *properties-fragment* to a dictionary mapping property names to values / xref uriid / link hrefs.
    
    Multiple properties with the same name will produce an array of values in the output dictionary.

    :param fragment: A valid properties-fragment
    :type fragment: str
    :raises TypeError: If the fragment cannot be parsed as xml.
    :raises NotImplementedError: If the property datatype attribute is present and is not one of; xref, link.
    :raises RuntimeError: If the fragment contains no properties.
    :return: A dictionary mapping property names to their values.
    :rtype: dict
    """
    if isinstance(fragment, str):
        fragment = BeautifulSoup(fragment, features='xml')
    elif not isinstance(fragment, Tag):
        fragment = BeautifulSoup(str(fragment), features='xml')
    
    d = defaultdict(list)
    for property in fragment("property"):
        if 'value' in property.attrs:
            d[property['name']].append(property['value'])
        elif 'datatype' in property.attrs:
            if property['datatype'] == 'xref':
                d[property['name']].append(property.xref['uriid'])
            elif property['datatype'] == 'link':
                d[property['name']].append(property.link['href'])
            else:
                raise NotImplementedError('Unimplemented property type')
    
    return {k: (v if len(v) > 1 else v[0]) for k, v in d.items()}


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
                <property name="template_version"     title="Template version"   value="6.1" />
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
                <property name="role"       title="DNS Role"    datatype="xref" >
                    <xref frag="default" uriid="" />
                </property>
            </properties-fragment>

        </section>

        <section id="records" title="DNS Records" />

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
                <property name="template_version"     title="Template version"   value="3.1" />
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
        
        <section id="records" title="PTR Records" />
        
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
                <property name="type" title="Node Type" value="#!type" />
                <property name="location" title="Location" value="#!location" />
            </properties-fragment>

        </section>

        <section id="body" />

        <section id="footer" />

    </document>
'''

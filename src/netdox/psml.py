"""
Provides some useful functions and constants for generating and manipulating PSML using BeautifulSoup4.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import TYPE_CHECKING, Iterable, Mapping, Any

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
        title: str,
        value: str = None,
        xref_href: str = None,
        xref_docid: str = None,
        xref_uriid: str = None,
        link_url: str = None,
        frag: str = 'default',
        namespace: str = None,
        prefix: str = None,
        attrs: Mapping[str, Any] = {}
    ) -> None:
        """
        Basic constructor.

        :param name: Value for the required name attribute.
        :type name: str
        :param title: Value for the required title attribute.
        :type title: str
        :param value: Value for the value attribute, defaults to None
        :type value: str, optional
        :param xref_href: Path to the xref destination. Ignored if value is present. Defaults to None
        :type xref_href: str, optional
        :param xref_docid: Docid of the xref destination. Ignored if value is present. Defaults to None
        :type xref_docid: str, optional
        :param xref_uriid: URIID of the xref destination. Ignored if value is present. Defaults to None
        :type xref_uriid: str, optional
        :param frag: Value for the required frag attribute on the child xref element, defaults to 'default'
        :type frag: str, optional
        :param namespace: Namespace for the tag, defaults to None
        :type namespace: str, optional
        :param prefix: Prefix for the tag, defaults to None
        :type prefix: str, optional
        :param attrs: Any attributes to set on the property tag, defaults to None
        :type attrs: Mapping[str, Any], optional
        :raises AttributeError: If value AND all the xref_* parameters are unset.
        """
        _attrs = {'name': name, 'title': title}
        xref_params = {'href': xref_href, 'docid': xref_docid, 'uriid': xref_uriid}
        xref_attrs = {}

        if value is not None:
            _attrs['value'] = value
        elif any(xref_params.values()):
            _attrs['datatype'] = 'xref'
            xref_attrs = {k: v for k, v in xref_params.items() if v is not None}
        elif link_url:
            _attrs['datatype'] = 'link'
        else:
            raise AttributeError('Property must have at least one of: value, xref_href, xref_docid, xref_uriid')
        
        super().__init__(
            name = 'property', 
            is_xml = True, 
            can_be_empty_element = True, 
            namespace = namespace, 
            prefix = prefix, 
            attrs = _attrs | attrs
        )

        if xref_attrs:
            self.append(Tag(
                is_xml=True, 
                can_be_empty_element = True, 
                name = 'xref', 
                attrs = {'frag': frag} | xref_attrs
            ))
        elif link_url:
            self.append(Tag(
                is_xml=True, 
                can_be_empty_element = True, 
                name = 'link', 
                attrs = {'href': link_url}
            ))


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
        PropertiesFragment(id = id_prefix + str(count), properties = [
            Property(
                name = p_name, 
                title = p_title, 
                xref_docid = docid_prefix + value.replace(".","_")),
            Property(
                name = 'source', 
                title = 'Source Plugin', 
                value = plugin
            )
        ])
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

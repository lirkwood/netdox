from __future__ import annotations

import re
from typing import TYPE_CHECKING, Iterable, Tuple

from bs4 import BeautifulSoup, Tag

if TYPE_CHECKING:
    from networkobjs import NetworkObject

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
        re.sub(f'#!{attribute}', value, template)
    return BeautifulSoup(template, features = 'xml')

def propertyXref(
        doc: BeautifulSoup, 
        p_name: str, 
        p_title: str, 
        docid: str, 
        frag: str = 'default'
    ) -> Tag:
    """
    Return a property with a child xref

    :param p_name: The name attribute for the property
    :type p_name: str
    :param p_title: The title attribute for the property
    :type p_title: str
    :param docid: The docid for the xref
    :type docid: str
    :param frag: The fragment for the xref, defaults to 'default'
    :type frag: str, optional
    :return: A bs4 Tag containing a property and its child xref.
    :rtype: Tag
    """
    property = doc.new_tag('property', attrs = {
        'name': p_name,
        'title': p_title,
        'datatype': 'xref'
    })
    property.append(doc.new_tag('xref', frag = frag, docid = docid))
    return property

def recordset2pfrags(
        doc: BeautifulSoup, 
        recordset: Iterable[Tuple[str, str]], 
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
    for value, plugin in recordset:
        frag = doc.new_tag('properties-fragment', id = f'{id_prefix}{str(count)}')
        frag.append(propertyXref(
            p_name = p_name,
            p_title = p_title,
            docid = f'{docid_prefix}{value.replace(".","_")}'
        ))
        frag.append(doc.new_tag('property', attrs = {'name': 'source', 'title': 'Source Plugin', 'value': plugin}))
        frags.append(frag)
        count += 1
    return frags


#############
# Templates #
#############

MIN_DOC = '<document level="portable" type="" xmlns:t="http://pageseeder.com/psml/template" />'

DOMAIN_TEMPLATE = '''
    <document type="domain" level="portable" xmlns:t="http://pageseeder.com/psml/template">

        <documentinfo>
            <uri docid="#!docid" title="#!name">
                <labels>show-reversexrefs</labels>
            </uri>
        </documentinfo>

        <metadata>
            <properties>
                <property name="template_version"     title="Template version"   value="6.0" />
            </properties>
        </metadata>

        <section id="title">
            <fragment id="title">
                <heading level="2">Domain name</heading>
                <heading level="1">#!name</heading>                    
            </fragment>
        </section>
        
        <section id="details">

            <properties-fragment id="info">
                <property name="name"       title="Name"        value="#!name" />
                <property name="root"       title="Root Domain" value="#!root" />
                <property name="role"       title="DNS Role"    datatype="xref" />
                <property name="location"   title="Location"    value="#!location" />
                <property name="node"       title="Node"        datatype="xref" />
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
                <labels>show-reversexrefs<xsl:value-of select="$labels"/></labels>
            </uri>
        </documentinfo>

        <metadata>
            <properties>
                <property name="template_version"     title="Template version"   value="2.2" />
            </properties>
        </metadata>

        <section id="title">
            <fragment id="title">
                <heading level="2">IP Address</heading>
                <heading level="1">#!name</heading>
            </fragment>
        </section>

        <section id="details" title="details">
        
            <properties-fragment id="addresses">
                <property name="ipv4"               title="IP"                  value="" /> 
                <property name="subnet"             title="Subnet"              value="" />
                <property name="location"           title="Location"            value="" />
                <property name="nat"                title="NAT Destination"     datatype="xref" />
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
                <labels>show-reversexrefs</labels>
            </uri>
        </documentinfo>

        <metadata>
            <properties>
                <property name="template_version"     title="Template version"   value="1.0" />
            </properties>
        </metadata>

        <section id="title">
            <fragment id="title">
                <heading level="2">Node</heading>
                <heading level="1">#!name</heading>                    
            </fragment>
        </section>
        
        <section id="details">

            <properties-fragment id="info">
                <property name="nodename" title="Name" value="#!name" />
                <property name="nodetype" title="Node Type" value="#!type" />
                <property name="location" title="Location" value="#!location" />
            </properties-fragment>

        </section>

        <section id="body" />

        <section id="footer" />

    </document>
'''
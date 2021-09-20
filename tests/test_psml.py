from netdox import objs, psml
from test_nwobjs import domain, ipv4, network, node
from pytest import raises, fixture


# n.b. attrs are alphabetically ordered
def test_Property_value():
    """
    Tests the Property class with the value attribute.
    """
    assert (
        str(psml.Property('test_name', 'Test Title', 'test_value')) ==
        '<property name="test_name" title="Test Title" value="test_value"/>' 
    )

def test_Property_href():
    """
    Tests the Property class with the xref_href attribute.
    """
    assert (
        str(psml.Property('test_name', 'Test Title', xref_href = '/test/path')) ==
        '<property datatype="xref" name="test_name" title="Test Title">'
        +'<xref frag="default" href="/test/path"/>'
        +'</property>' 
    )

def test_Property_docid():
    """
    Tests the Property class with the xref_docid attribute.
    """
    assert (
        str(psml.Property('test_name', 'Test Title', xref_docid = '_test_docid_')) ==
        '<property datatype="xref" name="test_name" title="Test Title">'
        +'<xref docid="_test_docid_" frag="default"/>'
        +'</property>' 
    )

def test_Property_uriid():
    """
    Tests the Property class with the xref_uriid attribute.
    """
    assert (
        str(psml.Property('test_name', 'Test Title', xref_uriid = 7357)) ==
        '<property datatype="xref" name="test_name" title="Test Title">'
        +'<xref frag="default" uriid="7357"/>'
        +'</property>' 
    )

def test_Property_url():
    """
    Tests the Property class with the link_url attribute.
    """
    assert (
        str(psml.Property('test_name', 'Test Title', link_url = 'https://sub.domain.com/uri')) ==
        '<property datatype="link" name="test_name" title="Test Title">'
        +'<link href="https://sub.domain.com/uri"/>'
        +'</property>' 
    )

def test_Property_none():
    with raises(AttributeError):
        psml.Property('test_name', 'Test Title')

def test_PropertiesFragment():
    """
    Tests the PropertiesFragment class with no properties
    """
    assert (
        str(psml.PropertiesFragment(id = 'test_id')) == 
        '<properties-fragment id="test_id"/>'
    )

def test_PropertiesFragment_withprop():
    """
    Tests the PropertiesFragment class with a property in it's constructor.
    """
    assert (
        str(psml.PropertiesFragment(id = 'test_id', properties = [
            psml.Property('test_name', 'Test Title', 'test_value')
        ])) ==
        '<properties-fragment id="test_id">'
        +'<property name="test_name" title="Test Title" value="test_value"/>'
        +'</properties-fragment>'
    )


def test_populate_domain(domain: objs.Domain):
    """
    Tests the populate function output for a Domain.
    """
    document = psml.populate(psml.DOMAIN_TEMPLATE, domain)
    assert document.find('property', attrs={'name': 'name'})['value'] == domain.name
    assert document.find('property', attrs={'name': 'zone'})['value'] == domain.zone

def test_populate_ipv4(ipv4: objs.IPv4Address):
    """
    Tests the populate function output for an IPv4Address.
    """
    document = psml.populate(psml.IPV4ADDRESS_TEMPLATE, ipv4)
    assert document.find('property', attrs={'name': 'ipv4'})['value'] == ipv4.name
    assert document.find('property', attrs={'name': 'subnet'})['value'] == ipv4.subnet

def test_populate_node(node: objs.DefaultNode):
    """
    Tests the populate function output for a Node.
    """
    document = psml.populate(psml.NODE_TEMPLATE, node)
    assert document.find('property', attrs={'name': 'name'})['value'] == node.name
    assert document.find('property', attrs={'name': 'type'})['value'] == node.type


def test_recordset2pfrags():
    """
    Tests the recordset2pfrags function.
    """
    # dict emulates ordered record set
    # as they both implement an ``items`` method
    records = {
        'record 1': 'source 1',
        'record 2': 'source 1',
        'record 3': 'source 2'
     }

    assert psml.recordset2pfrags(
        records, 'pfrag_', 'docid_', 'propname', 'Prop Title'
    ) == [
        psml.PropertiesFragment('pfrag_0', properties=[
            psml.Property('propname', 'Prop Title', xref_docid='docid_record 1'),
            psml.Property('source', 'Source Plugin', 'source 1'),
        ]),
        psml.PropertiesFragment('pfrag_1', properties=[
            psml.Property('propname', 'Prop Title', xref_docid='docid_record 2'),
            psml.Property('source', 'Source Plugin', 'source 1'),
        ]),
        psml.PropertiesFragment('pfrag_2', properties=[
            psml.Property('propname', 'Prop Title', xref_docid='docid_record 3'),
            psml.Property('source', 'Source Plugin', 'source 2'),
        ]),
    ]

def test_pfrag2dict():
    """
    Tests the pfrag2dict function
    """
    pfrag = psml.PropertiesFragment(id='foo', properties = [
        psml.Property('valprop','', 'some value'),
        psml.Property('valpropmulti','', 'some value 1'),
        psml.Property('valpropmulti','', 'some value 2'),
        psml.Property('xrefprop','', xref_uriid = '9999'),
        psml.Property('linkprop','', link_url = 'https://some.domain.com/')
    ]) 
    result = {
        'valprop': 'some value',
        'valpropmulti': [
            'some value 1',
            'some value 2'
        ],
        'xrefprop': '9999',
        'linkprop': 'https://some.domain.com/'
    }
    class NotString:
        """Some class that can be converted to a string."""
        def __init__(self, string): 
            self.string = str(string)
        def __repr__(self): 
            return self.string

    assert psml.pfrag2dict(pfrag) == result
    assert psml.pfrag2dict(str(pfrag)) == result
    assert psml.pfrag2dict(NotString(pfrag)) == result
    assert psml.pfrag2dict('') == {}
import pytest
from netdox import psml, objs

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


@pytest.fixture
def network():
    return objs.Network()
    
@pytest.fixture
def domain(network: objs.Network):
    return objs.Domain(network, 'sub.domain.com', 'domain.com')

@pytest.fixture
def ipv4(network: objs.Network):
    return objs.IPv4Address(network, '192.168.0.0')

@pytest.fixture
def node(network: objs.DefaultNode):
    return objs.DefaultNode(network, 'test_name', '192.168.0.0')


def test_populate_domain(domain: objs.Domain):
    document = psml.populate(psml.DOMAIN_TEMPLATE, domain)
    assert document.find('property', attrs={'name': 'name'})['value'] == 'sub.domain.com'
    assert document.find('property', attrs={'name': 'zone'})['value'] == 'domain.com'

def test_populate_ipv4(ipv4: objs.IPv4Address):
    document = psml.populate(psml.IPV4ADDRESS_TEMPLATE, ipv4)
    assert document.find('property', attrs={'name': 'ipv4'})['value'] == '192.168.0.0'
    assert document.find('property', attrs={'name': 'subnet'})['value'] == '192.168.0.0/24'

def test_populate_node(node: objs.DefaultNode):
    assert False
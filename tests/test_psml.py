from bs4 import BeautifulSoup
from netdox import psml, nwobjs
from test_nwobjs import domain, ipv4, network, node
from pytest import raises, fixture

class TestXRef:
    URIID = '7357'

    def test_uriid(self):
        assert (
            str(psml.XRef(uriid = self.URIID)) == 
            f'<xref frag="default" uriid="{self.URIID}"></xref>'
        )

    def test_docid(self):
        assert (
            str(psml.XRef(docid='_test_docid_')) == 
            '<xref docid="_test_docid_" frag="default"></xref>'
        )

    def test_href(self):
        assert (
            str(psml.XRef(href = '/test/path')) == 
            '<xref frag="default" href="/test/path"></xref>'
        )

    def test_fragment(self):
        assert (
            str(psml.XRef(self.URIID, frag = 'test_frag')) == 
            f'<xref frag="test_frag" uriid="{self.URIID}"></xref>'
        )

    def test_attrs(self):
        assert (
            str(psml.XRef(self.URIID, attrs = {'key': 'value'})) == 
            f'<xref frag="default" key="value" uriid="{self.URIID}"></xref>'
        )

    def test_string(self):
        assert (
            str(psml.XRef(self.URIID, string = 'test_string')) == 
            f'<xref frag="default" uriid="{self.URIID}">test_string</xref>'
        )

class TestLink:
    URL = 'https://website.domain.com/'
    
    def test_constructor(self):
        assert (
            str(psml.Link(self.URL)) ==
            f'<link href="{self.URL}">{self.URL}</link>'
        )
    
    def test_attrs(self):
        assert (
            str(psml.Link(self.URL, {'key': 'value'})) ==
            f'<link href="{self.URL}" key="value">'
            + self.URL + '</link>'
        )
    
    def test_string(self):
        STRING = 'test_string'
        assert (
            str(psml.Link(self.URL, string = STRING)) ==
            f'<link href="{self.URL}">{STRING}</link>'
        )

class TestProperty:
    NAME = 'property_name'
    VALUE = 'property_value!'
    TITLE = 'Property Title'

    @fixture
    def property(self):
        return psml.Property(self.NAME, self.VALUE, self.TITLE)

    @fixture
    def property_XRef(self):
        return psml.Property(self.NAME, psml.XRef(TestXRef.URIID), self.TITLE)

    @fixture
    def property_Link(self):
        return psml.Property(self.NAME, psml.Link(TestLink.URL), self.TITLE)

    # n.b. attrs are alphabetically ordered
    def test_to_string(self, property):
        """
        Tests the Property class with the value attribute.
        """
        assert (
            str(property) ==
            f'<property name="{self.NAME}" title="{self.TITLE}" value="{self.VALUE}"/>' 
        )

    def test_XRef_string(self, property_XRef):
        """
        Tests the Property class with the xref_href attribute.
        """
        assert (
            str(property_XRef) ==
            f'<property datatype="xref" name="{self.NAME}" title="{self.TITLE}">'
            f'<xref frag="default" uriid="{TestXRef.URIID}"></xref></property>' 
        )

    def test_Link_string(self, property_Link):
        """
        Tests the Property class with the link_url attribute.
        """
        assert (
            str(property_Link) ==
            f'<property datatype="link" name="{self.NAME}" title="{self.TITLE}">'
            f'<link href="{TestLink.URL}">{TestLink.URL}</link></property>' 
        )

    def test_roundtrip_tag(self, property):
        assert psml.Property.from_tag(property) == property

    def test_XRef_tag(self, property_XRef):
        from_tag = psml.Property.from_tag(property_XRef)
        assert from_tag == property_XRef
        assert isinstance(from_tag.findChild(), psml.XRef)

    def test_Link_tag(self, property_Link):
        from_tag = psml.Property.from_tag(property_Link)
        assert from_tag == property_Link
        assert isinstance(from_tag.findChild(), psml.Link)

class TestPropertiesFragment:

    @fixture
    def mock_PropertiesFragment(self):
        return psml.PropertiesFragment('id', [
                psml.Property('name1', 'value1'),
                psml.Property('name1', 'value2'),
                psml.Property('name2', 'value3'),
                psml.Property('name3', 'value4')
            ])

    def test_constructor(self):
        """
        Tests the PropertiesFragment class with no properties
        """
        assert (
            str(psml.PropertiesFragment(id = 'test_id')) == 
            '<properties-fragment id="test_id"/>'
        )

    def test_constructor_withprop(self):
        """
        Tests the PropertiesFragment class with a property in it's constructor.
        """
        assert (
            str(psml.PropertiesFragment(id = 'test_id', properties = [
                psml.Property('test_name', 'test_value', 'Test Title')
            ])) ==
            '<properties-fragment id="test_id">'
            +'<property name="test_name" title="Test Title" value="test_value"/>'
            +'</properties-fragment>'
        )

    def test_to_dict(self, mock_PropertiesFragment):
        assert (
            {
                'name1': [
                    'value1', 
                    'value2'
                ],
                'name2': 'value3',
                'name3': 'value4'
            } == mock_PropertiesFragment.to_dict()
        )

    def test_from_dict(self, mock_PropertiesFragment):
        assert mock_PropertiesFragment == psml.PropertiesFragment.from_dict(
            mock_PropertiesFragment['id'],
            mock_PropertiesFragment.to_dict())


    def test_from_tag(self, mock_PropertiesFragment):
        assert mock_PropertiesFragment == psml.PropertiesFragment.from_tag(
            mock_PropertiesFragment)


def test_populate_domain(domain: nwobjs.Domain):
    """
    Tests the populate function output for a Domain.
    """
    document = psml.populate(psml.DOMAIN_TEMPLATE, domain)
    assert document.find('property', attrs={'name': 'name'})['value'] == domain.name
    assert document.find('property', attrs={'name': 'zone'})['value'] == domain.zone

def test_populate_ipv4(ipv4: nwobjs.IPv4Address):
    """
    Tests the populate function output for an IPv4Address.
    """
    document = psml.populate(psml.IPV4ADDRESS_TEMPLATE, ipv4)
    assert document.find('property', attrs={'name': 'ipv4'})['value'] == ipv4.name
    assert document.find('property', attrs={'name': 'subnet'})['value'] == ipv4.subnet

def test_populate_node(node: nwobjs.DefaultNode):
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
            psml.Property('propname', title = 'Prop Title', 
                value = psml.XRef(docid='docid_record 1')),
            psml.Property('source', title = 'Source Plugin', value = 'source 1'),
        ]),
        psml.PropertiesFragment('pfrag_1', properties=[
            psml.Property('propname', title = 'Prop Title', 
                value = psml.XRef(docid='docid_record 2')),
            psml.Property('source', title = 'Source Plugin', value = 'source 1'),
        ]),
        psml.PropertiesFragment('pfrag_2', properties=[
            psml.Property('propname', title = 'Prop Title', 
                value = psml.XRef(docid='docid_record 3')),
            psml.Property('source', title = 'Source Plugin', value = 'source 2'),
        ]),
    ]
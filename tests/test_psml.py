from netdox import objs, psml
from test_nwobjs import domain, ipv4, network, node
from pytest import raises, fixture

class TestXRef:

    def test_uriid(self):
        assert (
            str(psml.XRef(uriid = '7357')) == 
            '<xref frag="default" uriid="7357"></xref>'
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
            str(psml.XRef('7357', frag = 'test_frag')) == 
            '<xref frag="test_frag" uriid="7357"></xref>'
        )

    def test_attrs(self):
        assert (
            str(psml.XRef('7357', attrs = {'key': 'value'})) == 
            '<xref frag="default" key="value" uriid="7357"></xref>'
        )

    def test_string(self):
        assert (
            str(psml.XRef('7357', string = 'test_string')) == 
            '<xref frag="default" uriid="7357">test_string</xref>'
        )

class TestLink:
    
    def test_constructor(self):
        assert (
            str(psml.Link('https://website.domain.com/')) ==
            '<link href="https://website.domain.com/">https://website.domain.com/</link>'
        )
    
    def test_attrs(self):
        assert (
            str(psml.Link('https://website.domain.com/', {'key': 'value'})) ==
            '<link href="https://website.domain.com/" key="value">'
            +'https://website.domain.com/</link>'
        )
    
    def test_string(self):
        assert (
            str(psml.Link('https://website.domain.com/', string = 'test_string')) ==
            '<link href="https://website.domain.com/">test_string</link>'
        )

class TestProperty:

    # n.b. attrs are alphabetically ordered
    def test_Property_string(self):
        """
        Tests the Property class with the value attribute.
        """
        assert (
            str(psml.Property('test_name', 'test_value', 'Test Title')) ==
            '<property name="test_name" title="Test Title" value="test_value"/>' 
        )

    def test_Property_XRef(self):
        """
        Tests the Property class with the xref_href attribute.
        """
        assert (
            str(psml.Property('test_name', psml.XRef('7357'), 'Test Title')) ==
            '<property datatype="xref" name="test_name" title="Test Title">'
            +'<xref frag="default" uriid="7357"></xref>'
            +'</property>' 
        )

    def test_Property_Link(self):
        """
        Tests the Property class with the link_url attribute.
        """
        assert (
            str(psml.Property('test_name', psml.Link('https://sub.domain.com/uri'), 'Test Title')) ==
            '<property datatype="link" name="test_name" title="Test Title">'
            +'<link href="https://sub.domain.com/uri">https://sub.domain.com/uri</link>'
            +'</property>' 
        )

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

def test_pfrag2dict():
    """
    Tests the pfrag2dict function
    """
    pfrag = psml.PropertiesFragment(id='foo', properties = [
        psml.Property('valprop', 'some value'),
        psml.Property('valpropmulti', 'some value 1'),
        psml.Property('valpropmulti', 'some value 2'),
        psml.Property('xrefprop', psml.XRef('9999')),
        psml.Property('linkprop', psml.Link('https://some.domain.com/'))
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
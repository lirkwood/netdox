import bs4
from netdox import psml
from fixtures import *
from pytest import fixture

class TestXRef:
    URIID = '7357'

    def test_uriid(self):
        assert (
            str(psml.XRef(uriid = self.URIID)) == 
            f'<xref frag="default" uriid="{self.URIID}"/>'
        )

    def test_docid(self):
        assert (
            str(psml.XRef(docid='_test_docid_')) == 
            '<xref docid="_test_docid_" frag="default"/>'
        )

    def test_href(self):
        assert (
            str(psml.XRef(href = '/test/path')) == 
            '<xref frag="default" href="/test/path"/>'
        )

    def test_fragment(self):
        assert (
            str(psml.XRef(self.URIID, frag = 'test_frag')) == 
            f'<xref frag="test_frag" uriid="{self.URIID}"/>'
        )

    def test_attrs(self):
        assert (
            str(psml.XRef(self.URIID, attrs = {'key': 'value'})) == 
            f'<xref frag="default" key="value" uriid="{self.URIID}"/>'
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
    MULTI_VALUE = ['prop_value_1', 'prop_value_2', 'prop_value_3']
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

    @fixture
    def property_multiple(self):
        return psml.Property(self.NAME, self.MULTI_VALUE, self.TITLE)

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
            f'<xref frag="default" uriid="{TestXRef.URIID}"/></property>' 
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

    def test_multiple_string(self, property_multiple):
        value_str = ''.join([f'<value>{val}</value>' for val in self.MULTI_VALUE])
        assert (
            str(property_multiple) == 
            f'<property multiple="true" name="{self.NAME}" title="{self.TITLE}">'
            + value_str + '</property>'
        )

    def test_roundtrip_tag(self, property: psml.Property):
        assert psml.Property.from_tag(property.tag) == property

    def test_XRef_tag(self, property_XRef: psml.Property):
        from_tag = psml.Property.from_tag(property_XRef.tag)
        assert from_tag == property_XRef
        assert isinstance(from_tag.value, psml.XRef)

    def test_Link_tag(self, property_Link: psml.Property):
        from_tag = psml.Property.from_tag(property_Link.tag)
        assert from_tag == property_Link
        assert isinstance(from_tag.value, psml.Link)

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

    def test_from_dict(self, mock_PropertiesFragment: psml.PropertiesFragment):
        assert mock_PropertiesFragment == psml.PropertiesFragment.from_dict(
            mock_PropertiesFragment.tag['id'],
            mock_PropertiesFragment.to_dict())


    def test_from_tag(self, mock_PropertiesFragment: psml.PropertiesFragment):
        assert mock_PropertiesFragment == psml.PropertiesFragment.from_tag(
            mock_PropertiesFragment.tag)
        
        
class TestFragment:
    
    @fixture
    def mock_Fragment(self) -> psml.Fragment:
        content = bs4.Tag(name = 'para', is_xml = True)
        content.string = 'Test string :)'
        return psml.Fragment(
            'test_id',
            [content],
            {'attr1': 'value1'}
        )
    
    def test_from_tag(self, mock_Fragment: psml.Fragment):
        assert str(mock_Fragment.tag) == str(psml.Fragment.from_tag(
            mock_Fragment.tag).tag)
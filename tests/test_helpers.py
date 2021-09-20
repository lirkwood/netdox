import pytest
from conftest import LOCATIONS, hide_file
from netdox import utils
from netdox.objs import helpers, nwobjs
from test_nwobjs import network, domain, ipv4, node
from lxml import etree


@pytest.fixture
def locator():
    return helpers.Locator()

class TestLocator:
    
    def test_constructor(self, hide_file):
        assert helpers.Locator().location_map == LOCATIONS
        hide_file(utils.APPDIR + 'cfg/locations.json')
        assert helpers.Locator().location_map == {}

    def test_locate(self, locator: helpers.Locator):
        assert locator.locate(['192.168.0.0']) == 'Subnet0'
        assert locator.locate(['192.168.0.0', '192.168.0.255']) == 'Subnet0'

        assert locator.locate(['192.168.1.0']) == 'Subnet1or2'
        assert locator.locate(['192.168.1.0', '192.168.2.255']) == 'Subnet1or2'

        assert locator.locate(['192.168.0.0', '192.168.1.0']) == None


@pytest.fixture
def psml_schema():
    return etree.XMLSchema(file = utils.APPDIR+ 'src/psml.xsd')

class TestPSMLWriter:

    def test_serialise_domain(self, domain: nwobjs.Domain, psml_schema: etree.XMLSchema):
        """
        Assert that the serialise method generates valid PSML from a Domain.
        """
        helpers.PSMLWriter().serialise(domain)
        assert psml_schema.validate(etree.parse(domain.outpath))

    def test_serialise_ipv4(self, ipv4: nwobjs.IPv4Address, psml_schema: etree.XMLSchema):
        """
        Assert that the serialise method generates valid PSML from a IPv4Address.
        """
        helpers.PSMLWriter().serialise(ipv4)
        assert psml_schema.validate(etree.parse(ipv4.outpath))

    def test_serialise_node(self, node: nwobjs.Node, psml_schema: etree.XMLSchema):
        """
        Assert that the serialise method generates valid PSML from a Node.
        """
        helpers.PSMLWriter().serialise(node)
        assert psml_schema.validate(etree.parse(node.outpath))
        

class TestRecordSet:

    @pytest.mark.parametrize('type', ['A', 'PTR', 'CNAME', 'NAT'])
    def test_constructor(self, type: str):
        recordset = helpers.RecordSet(type)
        assert recordset.record_type == helpers.RecordType[type]

    def test_add(self):
        recordset = helpers.RecordSet('CNAME')
        recordset.add('SomE.DomaiN.com   ', 'source')
        assert recordset.names == ['some.domain.com']

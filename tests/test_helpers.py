import pytest
from conftest import LOCATIONS, hide_file
from netdox import utils
from netdox import helpers, nwobjs
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

class TestRecordSet:

    @pytest.mark.parametrize('type', ['A', 'PTR', 'CNAME', 'NAT'])
    def test_constructor(self, type: str):
        recordset = helpers.RecordSet(type)
        assert recordset.record_type == helpers.RecordType[type]

    def test_add(self):
        recordset = helpers.RecordSet('CNAME')
        recordset.add('SomE.DomaiN.com   ', 'source')
        assert recordset.names == ['some.domain.com']
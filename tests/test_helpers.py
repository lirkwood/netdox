from conftest import hide_file, LOCATIONS
from netdox import utils
from netdox.objs import helpers
from pytest import fixture


@fixture
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
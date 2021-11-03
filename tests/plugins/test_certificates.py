from pytest import fixture
from netdox.plugins.certificates import analyze
from netdox.objs import Domain, Network
from netdox.psml import PropertiesFragment
from test_nwobjs import network

def test_analyze(network):
    """
    Tests that the analyze function correctly appends a PropertiesFragment
    to the footer of the provided domain.
    """
    domain = Domain(network, 'google.com')
    analyze(domain)

    assert len(domain.psmlFooter) == 1
    assert [
        'distinguishedname',
        'valid_from',
        'valid_to' 
    ] == sorted(domain.psmlFooter.pop().to_dict().keys())
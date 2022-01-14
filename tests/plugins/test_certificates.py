from netdox.plugins.certificates import analyze
from netdox import Domain
from fixtures import *

def test_analyze(network):
    """
    Tests that the analyze function correctly appends a PropertiesFragment
    to the footer of the provided domain.
    """
    domain = Domain(network, 'google.com')
    analyze(domain)

    footer_str = str(domain.psmlFooter)
    for propname in [
        'distinguishedname',
        'valid_from',
        'valid_to' 
    ]:
        assert propname in footer_str
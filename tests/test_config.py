from bs4 import BeautifulSoup
from netdox import config, psml
from fixtures import *

def test_generate_template():
    attrs = {'attr1', 'attr2', 'attr3'}
    template = BeautifulSoup(config.generate_template(attrs), 'xml')
    frag_dict = psml.PropertiesFragment.from_tag(
        template.find('t:fragment', type = 'label').find('properties-fragment')
    )

    assert {'label': None} | dict.fromkeys(attrs, None) == frag_dict.to_dict()


class TestNetworkConfig:

    def test_psml_roundtrip(self, network_config: config.NetworkConfig):
        assert network_config == config.NetworkConfig.from_psml(
            network_config.to_psml())

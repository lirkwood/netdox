from bs4 import BeautifulSoup
from netdox import config, psml
import pytest

def test_generate_template():
    attrs = {'attr1', 'attr2', 'attr3'}
    template = BeautifulSoup(config.generate_template(attrs), 'xml')
    frag_dict = psml.PropertiesFragment.from_tag(
        template.find('t:fragment', type = 'label').find('properties-fragment')
    ).to_dict()

    assert {'label': ''} | dict.fromkeys(attrs, '') == frag_dict


class TestNetworkConfig:

    @pytest.fixture
    def mock_NetworkConfig(self):
        return config.NetworkConfig(
            ['domain.one', 'domain.two'], 
            {'label': {'key1': 'value1', 'key2': 'value2'}},
            {'999': {'label_one', 'label_two'}}
        )

    def test_psml_roundtrip(self, mock_NetworkConfig):
        assert mock_NetworkConfig == config.NetworkConfig.from_psml(
            mock_NetworkConfig.to_psml())

from netdox.objs import config
import pytest

class TestNetworkConfig:

    @pytest.fixture
    def mock_NetworkConfig(self):
        return config.NetworkConfig(['domain.one', 'domain.two'], {
            'label': {'key1': 'value1', 'key2': 'value2'}
        })

    def test_psml_roundtrip(self, mock_NetworkConfig):
        assert mock_NetworkConfig == config.NetworkConfig.from_psml(
            mock_NetworkConfig.to_psml())
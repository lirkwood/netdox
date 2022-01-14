from netdox import config
import pytest

class TestNetworkConfig:

    @pytest.fixture
    def mock_NetworkConfig(self):
        return config.NetworkConfig(
            ['domain.one', 'domain.two'], 
            {'label': {'key1': 'value1', 'key2': 'value2'}},
            {'999': {'label_one', 'label_two'}}
        )

    def test_psml_roundtrip(self, mock_NetworkConfig):
        print(mock_NetworkConfig.to_psml())
        assert mock_NetworkConfig == config.NetworkConfig.from_psml(
            mock_NetworkConfig.to_psml())
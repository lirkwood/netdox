from types import ModuleType
from netdox import NetworkManager, Network
from fixtures import network
import pytest
from os import mkdir
from shutil import rmtree
from importlib import import_module

class TestNetworkManager:

    def test_constructor(self, network: Network):
        NetworkManager(network = network)

    @pytest.fixture
    def mock_plugin_namespace(self) -> ModuleType:
        namespace = '_test_plugins'
        mkdir(namespace)
        with open(f'{namespace}/test.py', 'w') as stream:
            stream.write('assert False')

        yield import_module(namespace)

        rmtree(namespace)
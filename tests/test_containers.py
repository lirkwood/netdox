from typing import cast
from conftest import randstr
from fixtures import *
from netdox import IPv4Address, Network
from netdox import iptools
from netdox.iptools import subn_iter
from netdox.nodes import Node, ProxiedNode
from netdox.app import PluginManager
from pytest import fixture, raises


class TestIPv4AddressSet:

    def test_fillSubnets(self, network: Network):
        """
        Tests that the fillSubnets method correctly populates existing subnets.
        """
        network.ips.fillSubnets()
        assert set(network.ips.objects) == {
            ip for subnet in network.config.subnets for ip in subn_iter(subnet)}


class TestNodeSet:

    def test_addRef(self, node: Node, randstr: str):
        node.network.nodes.addRef(node, randstr)
        assert node.network.nodes[randstr] is node

        with raises(KeyError):
            node.network.nodes['test']


class TestDomainSet:

    ...


class TestNetwork:

    def test_resolveRefs(self, network: Network):
        network.ips['0.0.0.0'].link('domain.com', '')
        network.domains['domain.com'].link('sub.domain.com', '')
        network.domains['sub.domain.com'].link('othersub.domain.com', '')
        network.domains['sub.domain.com'].link('target.domain.com', '')

        assert network.resolvesTo('0.0.0.0', 'domain.com')
        assert network.resolvesTo('0.0.0.0', 'sub.domain.com')
        assert network.resolvesTo('0.0.0.0', 'target.domain.com')

    def test_dump(self, network: Network):
        network.dump()
        Network.from_dump()

    # @fixture
    # def network_from_psml(self, plugin_mgr: PluginManager) -> Network:
    #     return Network.from_psml('resources/network', plugin_mgr.nodes)

    # def test_network_nodes(self, network_from_psml: Network):
    #     nodes = network_from_psml.nodes
    #     domains = network_from_psml.domains

    #     assert nodes['192.168.13.104'].ips == {
    #         '192.168.13.104', '103.127.18.104'}

    #     assert domains['netdox.allette.com.au'].node is \
    #         nodes['production_netdox-allette-com-au']

    #     assert nodes['production_netdox-allette-com-au'].domains == {
    #         'netdox.allette.com.au'}

    #     assert nodes['production_netdox-allette-com-au'].notes == \
    #         'These are some notes!'
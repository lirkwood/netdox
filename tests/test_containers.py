from conftest import randstr
from fixtures import node, network
from netdox import IPv4Address, Network
from netdox.iptools import subn_iter
from netdox.nodes import Node
from pytest import fixture, raises


class TestIPv4AddressSet:

    def test_fillSubnets(self, network: Network):
        """
        Tests that the fillSubnets method correctly populates existing subnets.
        """
        IPv4Address(network, '192.168.0.0')
        network.ips.fillSubnets()
        assert set(network.ips.objects) == {ip for ip in subn_iter('192.168.0.0/24')}


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

    def test_serialise(self, network: Network):
        network.dump()
        Network.fromDump()

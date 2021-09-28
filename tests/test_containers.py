from random import choices
from string import ascii_letters
from pytest import raises
from netdox.objs import Network, IPv4Address
from netdox.objs.nwobjs import Node
from netdox.iptools import subn_iter
from test_nwobjs import network, node

class TestIPv4AddressSet:
    def test_fillSubnets(self, network: Network):
        """
        Tests that the fillSubnets method correctly populates existing subnets.
        """
        IPv4Address(network, '192.168.0.0')
        network.ips.fillSubnets()
        assert set(network.ips.objects) == {ip for ip in subn_iter('192.168.0.0/24')}


class TestNodeSet:
    def test_addRef(self, node: Node):
        ref = ''.join(choices(ascii_letters, k = 20))
        node.network.nodes.addRef(node, ref)
        assert node.network.nodes[ref] is node

        with raises(KeyError):
            node.network.nodes['test']

    def test_resolveRefs(self, node: Node):
        net = Network()
        net.ips['0.0.0.0'].link('domain.com', '')
        net.domains['domain.com'].link('sub.domain.com', '')
        net.domains['sub.domain.com'].link('othersub.domain.com', '')
        net.domains['sub.domain.com'].link('target.domain.com', '')

        assert net.resolvesTo('0.0.0.0', 'domain.com')
        assert net.resolvesTo('0.0.0.0', 'sub.domain.com')
        assert net.resolvesTo('0.0.0.0', 'target.domain.com')


class TestDomainSet:

    ...


class TestNetwork:

    def test_constructor(self):
        net = Network()
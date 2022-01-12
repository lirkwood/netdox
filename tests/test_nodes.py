from gc import collect, get_referrers

from lxml import etree
from netdox import Network, nodes, utils, dns
from netdox.psml import Fragment, Section
from pytest import fixture, raises
from fixtures import network, node

@fixture
def psml_schema():
    return etree.XMLSchema(file = utils.APPDIR+ 'src/psml.xsd')

class TestNode:
    
    def test_constructor(self, network: Network):
        """
        Tests that the Node constructor correctly adds it to the network and sets its attributes.
        """
        dns.Domain(network, 'sub1.domain.com').link('10.0.0.0', 'source')
        dns.Domain(network, 'sub2.domain.com').link('10.0.0.0', 'source')
        node = nodes.Node(
            network, 
            name = 'node', 
            identity = '_node_iDenTity_', 
            domains = ['test.domain.com'], 
            ips = ['192.168.0.1', '10.0.0.0'],
            labels = ['some_label']
        )

        assert network.nodes.objects == {node.identity: node}
        assert node.network is network

        assert node.identity == '_node_identity_'
        assert node.domains == {'test.domain.com', 'sub1.domain.com', 'sub2.domain.com'}
        assert node.ips == {'192.168.0.1', '10.0.0.0'}

    def test_merge(self, node: nodes.Node):
        """
        Tests that the Node merge method correctly copies information from the targeted object.
        """
        footer_frag = Fragment('id')
        node.psmlFooter.insert(footer_frag)

        new = nodes.Node(
            network = node.network,
            name = 'nodename',
            identity = node.identity,
            domains = ['nonexistent.domain.com'],
            ips = ['10.1.1.1'],
            labels = ['test-label']
        )

        assert new.domains == node.domains | set(['nonexistent.domain.com'])
        assert new.ips == node.ips | set(['10.1.1.1'])
        assert new.labels == node.labels | set(['test-label'])
        assert str(new.psmlFooter) == str(Section('footer', fragments = [footer_frag]))

    def test_location(self, node: nodes.Node):
        """
        Tests that the location property returns the correct value.
        """
        assert node.location == node.network.locator.locate(node.ips)

        node.ips = set()
        assert node.location == '—'

        node.location = 'test value'
        assert node.location == 'test value'

        node.ips = {'192.168.0.0', '192.168.0.1'}
        assert node.location == 'test value'

        del node.location
        assert node.location == node.network.locator.locate({'192.168.0.0', '192.168.0.1'})

    def test_serialise(self, node: nodes.Node, psml_schema: etree.XMLSchema):
        assert psml_schema.validate(etree.fromstring(bytes(str(node.to_psml()), 'utf-8')))


class TestDefaultNode:

    def test_constructor(self, network: Network):
        """
        Tests that the DefaultNode constructor correctly raises exceptions if private_ip is invalid.
        """
        with raises(ValueError):
            nodes.DefaultNode(network, 'name', '0.0.0.0')
            nodes.DefaultNode(network, 'name', '!& invalid name &!')


class TestPlaceholderNode:

    def test_constructor(self, network: Network):
        """
        Tests that the PlaceholderNode constructor correctly adds it to the network and sets its attributes.
        """
        dns.IPv4Address(network, '10.0.0.0')
        original = nodes.DefaultNode(network, 'node1', '10.0.0.0')
        placeholder = nodes.PlaceholderNode(network, 'placeholder', ips = ['10.0.0.0'], labels = ['some_label'])
        assert placeholder is original

        dns.Domain(network, 'sub1.domain.com').node = nodes.DefaultNode(network, 'node1', '10.0.0.1')
        dns.Domain(network, 'sub2.domain.com').node = nodes.DefaultNode(network, 'node2', '10.0.0.2')
        with raises(AssertionError):
            nodes.PlaceholderNode(network, 'name', domains = ['sub1.domain.com','sub2.domain.com'])

    def test_merge(self, network: Network):
        dns.Domain(network, 'test.domain.com')
        dns.IPv4Address(network, '10.0.0.0')
        placeholder = nodes.PlaceholderNode(network, 'name', ['test.domain.com'], ['10.0.0.0'])

        placeholder.psmlFooter.insert(Fragment())
        network.nodes.addRef(placeholder, 'alias')

        node = nodes.DefaultNode(network, 'name', '10.0.0.0')
        
        assert network.nodes[placeholder.identity] is node
        assert network.nodes['alias'] is node
        assert network.ips['10.0.0.0'].node is node
        assert network.domains['test.domain.com'].node is node

        assert node.domains == set(['test.domain.com'])
        assert node.ips == set(['10.0.0.0'])
        assert node.psmlFooter == placeholder.psmlFooter


    def test_aliases(self, network: Network):
        """
        Tests that the aliases property correctly returns all names the node is referenced as in the NodeSet.
        """
        node = nodes.PlaceholderNode(network, 'name')
        network.nodes.addRef(node, 'test_alias_1')
        network.nodes.objects['test_alias_2'] = node
        assert node.aliases == {node.identity, 'test_alias_1', 'test_alias_2'}

        for alias in node.aliases:
            del network.nodes[alias]
        collect()
        assert not get_referrers(node)

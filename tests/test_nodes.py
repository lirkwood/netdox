from gc import collect, get_referrers
from bs4 import BeautifulSoup

from netdox import Network, nodes, utils, dns, iptools
from netdox.psml import Fragment
from pytest import fixture, raises
from fixtures import *

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
        assert new.psmlFooter == node.psmlFooter


    def test_location(self, node: nodes.Node, eg_subnet: str, eg_location: str):
        """
        Tests that the location property returns the correct value.
        """
        # No ips
        del node.location

        node.ips = set()
        assert node.location == '—'

        node.location = eg_location
        assert node.location == eg_location

        
        config_subnet = next(iter(node.network.config.subnets))

        # All ips outside of configured subnets
        del node.location

        node.ips = {'0.0.0.0', '255.255.255.255'}
        assert all([(not iptools.subn_contains(config_subnet, ip)) for ip in node.ips])
        assert node.location == '—'

        node.location = eg_location
        assert node.location == eg_location
        
        # Ip(s) inside configured subnet
        del node.location

        ip_iter = iter(iptools.subn_iter(config_subnet))
        node.ips = {next(ip_iter), next(ip_iter)}
        assert all([(iptools.subn_contains(config_subnet, ip)) for ip in node.ips])
        assert node.location == eg_location

        node.location = 'different_location'
        assert node.location == 'different_location'

    def test_to_psml(self, node: nodes.Node):
        assert utils.validate_psml(node.to_psml().encode('utf-8'))

    # TODO reactivate with safe node example
    # def test_from_psml(self):
    #     with open('resources/node.psml', 'r') as stream:
    #         soup = BeautifulSoup(stream.read(), 'xml')
    #     node = nodes.Node.from_psml(Network(), soup)

    #     assert node.name == 'prod.01.www.oxforddigital.com.au'
    #     assert node.identity == '10.0.0.120'
    #     assert node.type == nodes.Node.type
    #     assert node.domains == {'oxforddigital.com.au'}
    #     assert node.ips == {'54.79.82.213', '10.0.0.120'}
    #     assert node.notes == 'Node notes...'

    def test_organization_node(self, node: nodes.Node, eg_org_label: str, eg_org: str):
        assert node.organization == None

        node.organization = eg_org
        assert node.organization == eg_org

        del node.organization
        assert node.organization == None

        node.labels.add(eg_org_label)
        assert node.organization == eg_org


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
        with raises(RuntimeError):
            nodes.PlaceholderNode(network, 'name', domains = ['sub1.domain.com','sub2.domain.com'])

    def test_merge(self, network: Network):
        dns.Domain(network, 'test.domain.com')
        dns.IPv4Address(network, '10.0.0.0')
        placeholder = nodes.PlaceholderNode(network, 'name', ['test.domain.com'], ['10.0.0.0'])

        placeholder.psmlFooter.insert(Fragment('id'))
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

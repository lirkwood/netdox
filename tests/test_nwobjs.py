from gc import collect, get_referrers

from lxml import etree
from netdox import Network, iptools, nodes, utils, dns
from pytest import fixture, raises


@fixture
def network():
    return Network()
    
@fixture
def domain(network: Network):
    return dns.Domain(network, 'sub.domain.com', 'domain.com')

@fixture
def ipv4(network: Network):
    return dns.IPv4Address(network, '192.168.0.0')

@fixture
def node(network: Network):
    return nodes.Node(
        network = network,
        name = 'node_name',
        identity = '_node_identity_',
        domains = ['test.domain.com'],
        ips = ['0.0.0.0']
    )


@fixture
def psml_schema():
    return etree.XMLSchema(file = utils.APPDIR+ 'src/psml.xsd')

class TestDomain:

    def test_constructor(self, network: Network):
        """
        Tests that the Domain constructor correctly adds it to the network and sets its attributes.
        """
        has_label = dns.Domain(network, 'subdom1.zone.com', 'zone.com', ['has_label'])
        no_label = dns.Domain(network, 'subdom2.zone.com', 'zone.com', ['no_label'])

        assert network.domains.objects == {has_label.name: has_label, no_label.name: no_label}
        assert has_label.network is network
        assert no_label.network is network
        
        assert has_label.labels == set(['has_label']) | set(dns.Domain.DEFAULT_LABELS)
        assert no_label.labels == set(['no_label']) | set(dns.Domain.DEFAULT_LABELS)

        with raises(ValueError):
            dns.Domain(network, '!& invalid name &!')

    def test_default_zone(self, network: Network):
        domain = dns.Domain(network, 'sub.domain.com')
        assert domain.zone == 'domain.com'

    def test_link(self, domain: dns.Domain):
        """
        Tests that the Domain link method correctly creates forward and reverse refs.
        """
        dns.Domain(domain.network, 'test.domain.com')

        domain.link('192.168.0.1', 'source 1')
        domain.link('test.domain.com', 'source 2')

        assert domain.records.A.names == {('192.168.0.1')}
        assert domain.records.A.sources == {('source 1')}
        assert domain.records.CNAME.names == {('test.domain.com')}
        assert domain.records.CNAME.sources == {('source 2')}

        assert domain.network.ips['192.168.0.1'].backrefs.A.names == {(domain.name)}
        assert domain.network.ips['192.168.0.1'].backrefs.A.sources == {('source 1')}
        assert domain.network.domains['test.domain.com'].backrefs.CNAME.names == {(domain.name)}
        assert domain.network.domains['test.domain.com'].backrefs.CNAME.sources == {('source 2')}

        with raises(ValueError):
            domain.link('!& invalid name &!', 'source')


    def test_merge(self, network: Network):
        """
        Tests that the Domain merge method correctly copies information from the targeted object.
        """
        domain_name = 'subdom.zone.com'
        domain = dns.Domain(network, domain_name, 'zone.com', ['some_label'])
        domain.link('10.0.0.0', 'source 1')
        domain.psmlFooter.append('test item')
        network.ips['10.0.0.0'].link(domain_name, 'source 1')

        new = dns.Domain(network, domain_name, labels = ['other_label'])
        new.link('10.255.255.255', 'source 2')
        new.link('nonexistent.domain.com', 'source 2')
        new.psmlFooter.append('another test item')

        assert new.records.A.names == {'10.0.0.0', '10.255.255.255'}
        assert new.records.A.sources == {'source 1', 'source 2'}
        assert new.records.CNAME.names == {('nonexistent.domain.com')}
        assert new.records.CNAME.sources == {('source 2')}

        assert new.backrefs.A.names == {('10.0.0.0')}
        assert new.backrefs.A.sources == {('source 1')}
        assert new.backrefs.CNAME.names == set()
        assert new.backrefs.CNAME.sources == set()

        assert new.psmlFooter == ['test item', 'another test item']
        assert new.subnets == {'10.0.0.0/24', '10.255.255.0/24'}
        assert new.labels == set(['some_label', 'other_label']) | set(dns.Domain.DEFAULT_LABELS)

        with raises(AttributeError):
            domain.merge(dns.Domain(network, 'different.domain.com'))

    def test_serialise(self, domain: dns.Domain, psml_schema: etree.XMLSchema):
        assert psml_schema.validate(etree.fromstring(bytes(str(domain.to_psml()), 'utf-8')))


class TestIPv4Address:

    def test_constructor(self, network: Network):
        """
        Tests that the IPv4Address constructor correctly adds it to the network and sets its attributes.
        """
        private = dns.IPv4Address(network, '10.0.0.0')
        public = dns.IPv4Address(network, '255.255.255.255')

        assert network.ips.objects == {private.name: private, public.name: public}
        assert private.network is network
        assert public.network is network

        assert private.is_private
        assert not public.is_private

        assert private.subnet == iptools.sort(private.name)
        assert public.subnet == iptools.sort(public.name)

        with raises(ValueError):
            dns.IPv4Address(network, '!& invalid name &!')

    def test_link(self, ipv4: dns.IPv4Address):
        """
        Tests that the IPv4Address link method correctly creates forward and reverse refs.
        """
        ipv4.link('test.domain.com', 'source 2')
        ipv4.link('0.0.0.0', 'source 1')

        assert ipv4.records.PTR.names == {('test.domain.com')}
        assert ipv4.records.PTR.sources == {('source 2')}
        assert ipv4.records.CNAME.names == {('0.0.0.0')}
        assert ipv4.records.CNAME.sources == {('source 1')}

        assert ipv4.network.domains['test.domain.com'].backrefs.A.names == {(ipv4.name)}
        assert ipv4.network.domains['test.domain.com'].backrefs.A.sources == {('source 2')}
        assert ipv4.network.ips['0.0.0.0'].backrefs.CNAME.names == {(ipv4.name)}
        assert ipv4.network.ips['0.0.0.0'].backrefs.CNAME.sources == {('source 1')}

        with raises(ValueError):
            ipv4.link('!& invalid name &!', 'source')

    def test_merge(self, network: Network):
        """
        Tests that the IPv4Address merge method correctly copies information from the targeted object.
        """
        dns.Domain(network, 'test.domain.com') # remove this once backrefs are robust

        ipv4_name = '10.0.0.0'
        ipv4 = dns.IPv4Address(network, ipv4_name, ['some_label'])
        ipv4.translate('255.255.255.255', 'NAT source')
        ipv4.link('test.domain.com', 'source 1')
        ipv4.psmlFooter.append('test item')
        network.domains['test.domain.com'].link(ipv4_name, 'source 1')

        new = dns.IPv4Address(network, ipv4_name, ['other_label'])
        new.link('nonexistent.domain.com', 'source 2')
        new.link('10.255.255.255', 'source 2')
        new.psmlFooter.append('another test item')

        assert new.records.PTR.names == {'test.domain.com', 'nonexistent.domain.com'}
        assert new.records.PTR.sources == {'source 1', 'source 2'}
        assert new.records.CNAME.names == {('10.255.255.255')}
        assert new.records.CNAME.sources == {('source 2')}

        assert new.backrefs.A.names == {('test.domain.com')}
        assert new.backrefs.A.sources == {('source 1')}
        assert new.backrefs.CNAME.names == set()
        assert new.backrefs.CNAME.sources == set()

        assert new.labels == set(['some_label', 'other_label']) | set(dns.IPv4Address.DEFAULT_LABELS)
        assert new.psmlFooter == ['test item', 'another test item']
        assert new.NAT == {dns.NATEntry(new, network.ips['255.255.255.255'], 'NAT source')}

        with raises(AttributeError):
            ipv4.merge(dns.IPv4Address(network, '123.45.67.89'))

    def test_unused_record(self, ipv4: dns.IPv4Address):
        """
        Tests that the unused property updates correctly when a record is added to the IPv4Address.
        """
        assert ipv4.unused
        ipv4.link('test.domain.com', 'source')
        assert not ipv4.unused

    def test_unused_backref(self, ipv4: dns.IPv4Address):
        """
        Tests that the unused property updates correctly when a backref is added to the IPv4Address.
        """
        assert ipv4.unused
        ipv4.network.domains['test.domain.com'].link(ipv4.name, 'source')
        assert not ipv4.unused

    def test_unused_node(self, ipv4: dns.IPv4Address):
        """
        Tests that the unused property updates correctly when a node is added to the IPv4Address.
        """
        assert ipv4.unused
        ipv4.node = nodes.DefaultNode(ipv4.network, ipv4.name, ipv4.name)
        assert not ipv4.unused

    def test_serialise(self, ipv4: dns.IPv4Address, psml_schema: etree.XMLSchema):
        assert psml_schema.validate(etree.fromstring(bytes(str(ipv4.to_psml()), 'utf-8')))


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
        node.psmlFooter.append('footer tag')

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
        assert new.psmlFooter == ['footer tag']

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

        placeholder.psmlFooter.append('footer value')
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

from netdox import iptools, objs
from netdox.objs import nwobjs
from pytest import fixture, raises
from gc import collect, get_referrers


@fixture
def network():
    return objs.Network()
    
@fixture
def domain(network: objs.Network):
    return objs.Domain(network, 'sub.domain.com', 'domain.com')

@fixture
def ipv4(network: objs.Network):
    return objs.IPv4Address(network, '192.168.0.0')

@fixture
def node(network: objs.Network):
    return nwobjs.Node(
        network = network,
        name = 'node_name',
        docid = '_node_docid_',
        identity = '_node_identity_',
        domains = ['test.domain.com'],
        ips = ['0.0.0.0']
    )

@fixture
def node(network: objs.DefaultNode):
    return objs.DefaultNode(network, 'test_name', '192.168.0.0', labels = ['test_label'])


class TestDomain:

    def test_constructor(self, network: objs.Network):
        """
        Tests that the Domain constructor correctly adds it to the network and sets its attributes.
        """
        role = {
            'name': 'test_role',
            'domains':['subdom1.zone.tld']
        }
        network.domains._roles[role['name']] = role

        has_role = objs.Domain(network, 'subdom1.zone.tld', 'zone.tld', ['has_role'])
        no_role = objs.Domain(network, 'subdom2.zone.tld', 'zone.tld', ['no_role'])

        assert network.domains.objects == {has_role.name: has_role, no_role.name: no_role}
        assert has_role.network is network
        assert no_role.network is network
        
        assert has_role.role == role['name']
        assert has_role.labels == set(['has_role', 'show-reversexrefs'])

        assert no_role.role == 'default'
        assert no_role.labels == set(['no_role', 'show-reversexrefs'])

        with raises(ValueError):
            objs.Domain(network, '!& invalid name &!')

    def test_link(self, domain: objs.Domain):
        """
        Tests that the Domain link method correctly creates forward and reverse refs.
        """
        objs.Domain(domain.network, 'test.domain.com')

        domain.link('192.168.0.1', 'source 1')
        domain.link('test.domain.com', 'source 2')

        assert domain.records['A']._records == {('192.168.0.1', 'source 1')}
        assert domain.records['CNAME']._records == {('test.domain.com', 'source 2')}

        assert domain.network.ips['192.168.0.1'].backrefs['A'] == set([domain.name])
        assert domain.network.domains['test.domain.com'].backrefs['CNAME'] == set([domain.name])

        with raises(ValueError):
            domain.link('!& invalid name &!', 'source')


    def test_merge(self, network: objs.Network):
        """
        Tests that the Domain merge method correctly copies information from the targeted object.
        """
        domain_name = 'subdom.zone.tld'
        domain = objs.Domain(network, domain_name, 'zone.tld', ['some_label'])
        domain.link('10.0.0.0', 'source 1')
        domain.psmlFooter.append('test item')
        network.ips['10.0.0.0'].link(domain_name, 'source 1')

        new = objs.Domain(network, domain_name, labels = ['other_label'])
        new.link('10.255.255.255', 'source 2')
        new.link('nonexistent.domain.com', 'source 2')
        new.psmlFooter.append('another test item')

        assert new.records['A']._records == {('10.0.0.0', 'source 1'), ('10.255.255.255', 'source 2')}
        assert new.records['CNAME']._records == {('nonexistent.domain.com', 'source 2')}

        assert new.backrefs['PTR'] == set(['10.0.0.0'])
        assert new.backrefs['CNAME'] == set()

        assert new.labels == set(['show-reversexrefs', 'some_label', 'other_label'])
        assert new.psmlFooter == ['test item', 'another test item']
        assert new.subnets == {'10.0.0.0/24', '10.255.255.0/24'}

        with raises(AttributeError):
            domain.merge(objs.Domain(network, 'different.domain.tld'))


class TestIPv4Address:

    def test_constructor(self, network: objs.Network):
        """
        Tests that the IPv4Address constructor correctly adds it to the network and sets its attributes.
        """
        private = objs.IPv4Address(network, '10.0.0.0')
        public = objs.IPv4Address(network, '255.255.255.255')

        assert network.ips.objects == {private.name: private, public.name: public}
        assert private.network is network
        assert public.network is network

        assert private.is_private
        assert not public.is_private

        assert private.subnet == iptools.sort(private.name)
        assert public.subnet == iptools.sort(public.name)

        with raises(ValueError):
            objs.IPv4Address(network, '!& invalid name &!')

    def test_link(self, ipv4: objs.IPv4Address):
        """
        Tests that the IPv4Address link method correctly creates forward and reverse refs.
        """
        objs.Domain(ipv4.network, 'test.domain.com')

        ipv4.link('test.domain.com', 'source 2')
        ipv4.link('0.0.0.0', 'source 1')

        assert ipv4.records['PTR']._records == {('test.domain.com', 'source 2')}
        assert ipv4.records['CNAME']._records == {('0.0.0.0', 'source 1')}

        assert ipv4.network.domains['test.domain.com'].backrefs['PTR'] == set([ipv4.name])
        assert ipv4.network.ips['0.0.0.0'].backrefs['CNAME'] == set([ipv4.name])

        with raises(ValueError):
            ipv4.link('!& invalid name &!', 'source')

    def test_merge(self, network: objs.Network):
        """
        Tests that the IPv4Address merge method correctly copies information from the targeted object.
        """
        objs.Domain(network, 'test.domain.com') # remove this once backrefs are robust

        ipv4_name = '10.0.0.0'
        ipv4 = objs.IPv4Address(network, ipv4_name, ['some_label'])
        ipv4.nat = '255.255.255.255'
        ipv4.link('test.domain.com', 'source 1')
        ipv4.psmlFooter.append('test item')
        network.domains['test.domain.com'].link(ipv4_name, 'source 1')

        new = objs.IPv4Address(network, ipv4_name, ['other_label'])
        new.link('nonexistent.domain.com', 'source 2')
        new.link('10.255.255.255', 'source 2')
        new.psmlFooter.append('another test item')

        assert new.records['PTR']._records == {('test.domain.com', 'source 1'),('nonexistent.domain.com', 'source 2')}
        assert new.records['CNAME']._records == {('10.255.255.255', 'source 2')}

        assert new.backrefs['A'] == set(['test.domain.com'])
        assert new.backrefs['CNAME'] == set()

        assert new.labels == set(['show-reversexrefs', 'some_label', 'other_label'])
        assert new.psmlFooter == ['test item', 'another test item']
        assert new.nat == '255.255.255.255'

        with raises(AttributeError):
            ipv4.merge(objs.IPv4Address(network, '123.45.67.89'))

    def test_unused_record(self, ipv4: objs.IPv4Address):
        """
        Tests that the unused property updates correctly when a record is added to the IPv4Address.
        """
        assert ipv4.unused
        ipv4.link('test.domain.com', 'source')
        assert not ipv4.unused

    def test_unused_backref(self, ipv4: objs.IPv4Address):
        """
        Tests that the unused property updates correctly when a backref is added to the IPv4Address.
        """
        assert ipv4.unused
        ipv4.network.domains['test.domain.com'].link(ipv4.name, 'source')
        assert not ipv4.unused

    def test_unused_node(self, ipv4: objs.IPv4Address):
        """
        Tests that the unused property updates correctly when a node is added to the IPv4Address.
        """
        assert ipv4.unused
        ipv4.node = objs.DefaultNode(ipv4.network, ipv4.name, ipv4.name)
        assert not ipv4.unused


class TestNode:
    
    def test_constructor(self, network: objs.Network):
        """
        Tests that the Node constructor correctly adds it to the network and sets its attributes.
        """
        objs.Domain(network, 'sub1.domain.com').link('10.0.0.0', 'source')
        objs.Domain(network, 'sub2.domain.com').link('10.0.0.0', 'source')
        node = nwobjs.Node(
            network, 
            name = 'node', 
            docid = '_node_docid_', 
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

    def test_merge(self, node: nwobjs.Node):
        """
        Tests that the Node merge method correctly copies information from the targeted object.
        """
        node.psmlFooter.append('footer tag')

        new = nwobjs.Node(
            network = node.network,
            name = 'nodename',
            docid = '_node_docid_',
            identity = node.identity,
            domains = ['nonexistent.domain.com'],
            ips = ['10.1.1.1'],
            labels = ['test-label']
        )

        assert new.domains == node.domains | set(['nonexistent.domain.com'])
        assert new.ips == node.ips | set(['10.1.1.1'])
        assert new.labels == node.labels | set(['test-label'])
        assert new.psmlFooter == ['footer tag']

    def test_location(self, node: nwobjs.Node):
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


class TestDefaultNode:

    def test_constructor(self, network: objs.Network):
        """
        Tests that the DefaultNode constructor correctly raises exceptions if private_ip is invalid.
        """
        with raises(ValueError):
            objs.DefaultNode(network, 'name', '0.0.0.0')
            objs.DefaultNode(network, 'name', '!& invalid name &!')


class TestPlaceholderNode:

    def test_constructor(self, network: objs.Network):
        """
        Tests that the PlaceholderNode constructor correctly adds it to the network and sets its attributes.
        """
        objs.IPv4Address(network, '10.0.0.0')
        original = objs.DefaultNode(network, 'node1', '10.0.0.0')
        placeholder = nwobjs.PlaceholderNode(network, 'placeholder', ips = ['10.0.0.0'], labels = ['some_label'])
        assert placeholder is original

        objs.Domain(network, 'sub1.domain.com').node = objs.DefaultNode(network, 'node1', '10.0.0.1')
        objs.Domain(network, 'sub2.domain.com').node = objs.DefaultNode(network, 'node2', '10.0.0.2')
        with raises(AssertionError):
            nwobjs.PlaceholderNode(network, 'name', domains = ['sub1.domain.com','sub2.domain.com'])

    def test_merge(self, network: objs.Network):
        objs.Domain(network, 'test.domain.com')
        objs.IPv4Address(network, '10.0.0.0')
        placeholder = nwobjs.PlaceholderNode(network, 'name', ['test.domain.com'], ['10.0.0.0'])

        placeholder.psmlFooter.append('footer value')
        network.addRef(placeholder, 'alias')
        network.addRef(placeholder, '10.0.0.0') # defaultnode identity will be '10.0.0.0' => trigger merge

        node = objs.DefaultNode(network, 'name', '10.0.0.0')
        
        assert network.nodes[placeholder.identity] is node
        assert network.nodes['alias'] is node
        assert network.ips['10.0.0.0'].node is node
        assert network.domains['test.domain.com'].node is node

        assert node.domains == set(['test.domain.com'])
        assert node.ips == set(['10.0.0.0'])
        assert node.psmlFooter == placeholder.psmlFooter


    def test_aliases(self, network: objs.Network):
        """
        Tests that the aliases property correctly returns all names the node is referenced as in the NodeSet.
        """
        node = nwobjs.PlaceholderNode(network, 'name')
        network.addRef(node, 'test_alias_1')
        network.nodes.objects['test_alias_2'] = node
        assert node.aliases == {node.uuid, 'test_alias_1', 'test_alias_2'}

        for alias in node.aliases:
            del network.nodes[alias]
        collect()
        assert not get_referrers(node)
from netdox import objs
from pytest import fixture, raises


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
        
        assert has_role.role == role['name']
        assert has_role.labels == set(['has_role', 'show-reversexrefs'])

        assert no_role.role == 'default'
        assert no_role.labels == set(['no_role', 'show-reversexrefs'])

        no_role_shadow = objs.Domain(network, 'subdom2.zone.tld')
        assert network.domains[no_role.name] == no_role_shadow != no_role

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

    def test_merge(self, network: objs.Network):
        """
        Tests that the Domain merge method correctly copies information from the targeted object.
        """
        domain_name = 'subdom.zone.tld'
        domain = objs.Domain(network, domain_name, 'zone.tld', ['some_label'])
        domain.link('10.0.0.0', 'source 1')
        domain.psmlFooter.append('test item')
        domain.network.ips['10.0.0.0'].link(domain_name, 'source 2')

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
from pytest import raises, fixture
from netdox import Network, dns, iptools, nodes, psml
from fixtures import *
from lxml import etree

class TestDNSLink:

    def test_type_A(self, domain, ipv4):
        assert dns.DNSLink(domain, ipv4, '').type == dns.DNSRecordType.A

    def test_type_PTR(self, domain, ipv4):
        assert dns.DNSLink(ipv4, domain, '').type == dns.DNSRecordType.PTR

    def test_type_CNAME(self, domain, ipv4):
        assert dns.DNSLink(domain, domain, '').type == dns.DNSRecordType.CNAME
        assert dns.DNSLink(ipv4, ipv4, '').type == dns.DNSRecordType.CNAME

class TestDNSRecordSet:

    SOURCE = 'test source'

    @fixture
    def origin(self, domain):
        return domain

    @fixture
    def destination(self, ipv4):
        return ipv4

    @fixture
    def mock_record_set(self, origin, destination) -> dns.DNSRecordSet:
        set = dns.DNSRecordSet()
        set.add(dns.DNSLink(origin, destination, self.SOURCE))
        return set

    def test_to_psml(self, mock_record_set: dns.DNSRecordSet, destination: dns.DNSObject):
        record = next(iter(mock_record_set))
        assert (
            str(mock_record_set.to_psml()) ==
            f'<section id="records" title="DNS Records">'
            f'<properties-fragment id="{record.type.value}_record_0">'
            f'<property datatype="xref" name="{destination.type}" title="{record.type.value} record">'
            f'<xref docid="{destination.docid}" frag="default"/></property>'
            f'<property name="source" title="Source Plugin" value="test source"/>'
            f'</properties-fragment></section>'
        )

class TestDomain:

    MOCK_NAME = 'sub.domain.com'
    MOCK_ZONE = 'domain.com'
    MOCK_LABELS = {('some_label')}
    MOCK_FOOTER = psml.Section('footer', fragments = [psml.Fragment('id')])

    @fixture
    def mock_domain(self, network: Network) -> dns.Domain:
        domain = dns.Domain(network, self.MOCK_NAME, self.MOCK_ZONE,
            labels = self.MOCK_LABELS)
        domain.psmlFooter.extend(self.MOCK_FOOTER)
        domain.link('255.255.255.255', 'source 1')
        domain.link('test.domain.com', 'source 2')
        return domain

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

        assert domain.records.names == {'192.168.0.1', 'test.domain.com'}
        assert domain.records.sources == {'source 1', 'source 2'}

        ip_dest = domain.network.ips['192.168.0.1']
        assert ip_dest.backrefs.names == {(domain.name)}
        assert ip_dest.backrefs.sources == {('source 1')}

        domain_dest = domain.network.domains['test.domain.com']
        assert domain_dest.backrefs.names == {(domain.name)}
        assert domain_dest.backrefs.sources == {('source 2')}

        with raises(ValueError):
            domain.link('!& invalid name &!', 'source')


    def test_merge(self, mock_domain: dns.Domain):
        """
        Tests that the Domain merge method correctly copies information from the targeted object.
        """
        backref_name = '10.10.10.20'
        backref_source = 'backref_source'
        mock_domain.network.ips[backref_name].link(mock_domain, backref_source)
        
        new_labels = {('other_label')}
        new = dns.Domain(mock_domain.network, mock_domain.name, labels = new_labels)

        new_source = 'source 3'
        new_names = {'255.0.0.0', 'other.domain.com'}
        for name in new_names:
            new.link(name, new_source)

        assert new.records.names == new_names | mock_domain.records.names
        assert new.records.sources == {(new_source)} | mock_domain.records.sources

        assert new.backrefs.names == {(backref_name)}
        assert new.backrefs.sources == {(backref_source)}

        assert new.psmlFooter == mock_domain.psmlFooter
        assert not new.psmlFooter is mock_domain.psmlFooter
        assert new.labels == new_labels | mock_domain.labels

        with raises(AttributeError):
            domain.merge(dns.Domain(network, 'different.domain.com'))

    def test_serialise(self, domain: dns.Domain, psml_schema: etree.XMLSchema):
        assert psml_schema.validate(etree.fromstring(domain.to_psml().encode('utf-8')))

    def test_organization(self, mock_domain: dns.Domain, org: str, org_label: str):
        assert mock_domain.organization == None

        mock_domain.organization = org
        assert mock_domain.organization == org

        del mock_domain.organization
        assert mock_domain.organization == None

        mock_domain.labels.add(org_label)
        assert mock_domain.organization == org

class TestIPv4Address:

    MOCK_NAME = '10.0.0.0'
    MOCK_LABELS = {('some_label')}
    MOCK_FOOTER = psml.Section('footer', fragments = [psml.Fragment('id')])

    @fixture
    def mock_ipv4(self, network: Network) -> dns.IPv4Address:
        ipv4 = dns.IPv4Address(network, self.MOCK_NAME, self.MOCK_LABELS)
        ipv4.psmlFooter.extend(self.MOCK_FOOTER)
        ipv4.translate('255.255.255.255', 'NAT source')
        ipv4.link('test.domain.com', 'source 1')
        return ipv4

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

    def test_merge(self, mock_ipv4: dns.IPv4Address):
        """
        Tests that the IPv4Address merge method correctly copies information from the targeted object.
        """
        backref_name = 'test.domain.com'
        backref_source = 'backref_source'
        mock_ipv4.network.domains[backref_name].link(mock_ipv4, backref_source)

        new_labels = {('other_label')}
        new = dns.IPv4Address(mock_ipv4.network, mock_ipv4.name, new_labels)

        new_nat = new.network.ips['10.10.10.10']
        new_source = 'source 2'
        new.translate(new_nat, new_source)

        new_names = {'nonexistent.domain.com', '10.255.255.255'}
        for name in new_names:
            new.link(name, new_source)

        assert new.records.names == new_names | mock_ipv4.records.names
        assert new.records.sources == {(new_source)} | mock_ipv4.records.sources

        assert new.backrefs.names == {(backref_name)}
        assert new.backrefs.sources == {(backref_source)}

        assert new.labels == mock_ipv4.labels | new_labels
        assert str(new.psmlFooter) == str(mock_ipv4.psmlFooter)
        assert not new.psmlFooter is mock_ipv4.psmlFooter
        assert new.NAT == mock_ipv4.NAT | {dns.NATEntry(new, new_nat, new_source)}

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
        assert psml_schema.validate(etree.fromstring(ipv4.to_psml().encode('utf-8')))

    def test_organization(self, mock_ipv4: dns.Domain, org: str, org_label: str):
        assert mock_ipv4.organization == None

        mock_ipv4.organization = org
        assert mock_ipv4.organization == org

        del mock_ipv4.organization
        assert mock_ipv4.organization == None

        mock_ipv4.labels.add(org_label)
        assert mock_ipv4.organization == org

from pytest import fixture
from netdox import Network, utils, nodes, dns
from lxml import etree

@fixture
def network():
    return Network()

@fixture
def domain(network: Network):
    return dns.Domain(network, 'sub.domain.com')

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
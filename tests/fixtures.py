from pytest import fixture
from netdox import Network, utils, nodes, dns
from netdox.config import NetworkConfig
from lxml import etree

@fixture
def excluded_domain() -> str:
    return 'excluded.com'

@fixture
def attr_label() -> str:
    return 'attribute_label'

@fixture
def attr_label_attrs() -> dict:
    return {'attr1': 'value1'}

@fixture
def org() -> str:
    return 'organization_name'

@fixture
def org_label() -> str:
    return 'organization_label'

@fixture
def network_config(excluded_domain, attr_label, attr_label_attrs, org, org_label):
    return NetworkConfig(
        exclusions = [excluded_domain],
        labels = {attr_label: attr_label_attrs},
        organizations = {org: set([org_label])}
    )

@fixture
def network(network_config):
    return Network(config = network_config)

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
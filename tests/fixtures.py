from pytest import fixture
from netdox import Network, utils, nodes, dns
from netdox.config import NetworkConfig
from netdox.app import PluginManager
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
def eg_org() -> int:
    return 94549

@fixture
def eg_org_label() -> str:
    return 'organization_label'

@fixture
def eg_subnet() -> str:
    return '192.168.254.0/24'

@fixture
def eg_location() -> str:
    return 'eg_location'

@fixture
def network_config(excluded_domain, attr_label, attr_label_attrs, eg_org, eg_org_label, eg_subnet, eg_location):
    return NetworkConfig(
        exclusions = [excluded_domain],
        labels = {attr_label: attr_label_attrs},
        organizations = {eg_org: set([eg_org_label])},
        subnets = {eg_subnet: eg_location}
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


@fixture
def plugin_mgr():
    return PluginManager()
from netdox import objs
from pytest import fixture


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

from netdox import Network, Node, Domain, IPv4Address
from netdox.plugins.plantuml.diagram import NodeDiagramFactory
from netdox.psml import PropertiesFragment, Property, Link
from netdox.utils import config

EXTRA_ATTRS = {
    Node: 'type',
    Domain: 'zone',
    IPv4Address: 'subnet'
}

def runner(network: Network) -> None:
    factory = NodeDiagramFactory(**config('plantuml'))
    for node in network.nodes:
        url = factory.draw(node)
        node.psmlFooter.append(PropertiesFragment('diagram', properties = [
            Property('diagram', Link(url, string = factory.server), 'PlantUML Diagram')
        ]))

__stages__ = {'footers': runner}
__config__ = {
    'server': (lambda: 'www.plantuml.com/plantuml'),
    'https': (lambda: True)
}
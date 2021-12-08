from typing import Optional
from netdox import Network, Node, Domain, IPv4Address
from netdox.plugins.plantuml.diagram import NodeDiagramFactory
from netdox.psml import PropertiesFragment, Property, Link

EXTRA_ATTRS = {
    Node: 'type',
    Domain: 'zone',
    IPv4Address: 'subnet'
}

def runner(network: Network) -> None:
    factory = NodeDiagramFactory()
    for node in network.nodes:
        url = factory.draw(node)
        node.psmlFooter.append(PropertiesFragment('diagram', properties = [
            Property('diagram', Link(url), 'PlantUML Diagram')
        ]))

__stages__ = {'footers': runner}
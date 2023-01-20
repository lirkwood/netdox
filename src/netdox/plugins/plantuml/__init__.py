from netdox import Network, Node, Domain, IPv4Address
from netdox.app import LifecycleStage
from netdox.plugins.plantuml.diagram import NodeDiagramFactory
from netdox.psml import MediaFragment
from bs4 import BeautifulSoup
from netdox.utils import config

EXTRA_ATTRS = {
    Node: 'type',
    Domain: 'zone',
    IPv4Address: 'subnet'
}

def runner(network: Network) -> None:
    factory = NodeDiagramFactory(**config('plantuml'))
    for node in network.nodes:
        svg = factory.draw(node)
        node.psmlFooter.insert(MediaFragment(
            'diagram', 
            mediatype = 'image/svg+xml',
            content = BeautifulSoup(svg, 'xml').svg.extract()
        ))

__stages__ = {LifecycleStage.FOOTERS: runner}
__config__ = {
    'server': 'www.plantuml.com/plantuml',
    'https': True
}
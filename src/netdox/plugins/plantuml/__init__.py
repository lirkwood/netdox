from netdox import Network, Node, Domain, IPv4Address 
from netdox.app import LifecycleStage
from netdox.nodes import NoteHolder
from netdox.plugins.plantuml.diagram import NodeDiagramFactory
from netdox.psml import image_fragment
from netdox.utils import config
from .diagram import OUTDIR

from bs4 import BeautifulSoup
from shutil import rmtree
import os

EXTRA_ATTRS = {
    Node: 'type',
    Domain: 'zone',
    IPv4Address: 'subnet'
}


def init(_: Network) -> None:
    if os.path.exists(OUTDIR):
        rmtree(OUTDIR)
    os.mkdir(OUTDIR)

def runner(network: Network) -> None:
    diagram_dir = f'/ps/{config()["pageseeder"]["group"].replace("-","/")}/website/diagrams'
    factory = NodeDiagramFactory(**config('plantuml'))
    for node in network.nodes:
        if not isinstance(node, NoteHolder):
            factory.draw(node)
            node.psmlFooter.insert(image_fragment('diagram', f'{diagram_dir}/{node.docid}.svg'))

__stages__ = {
    LifecycleStage.INIT: init,
    LifecycleStage.FOOTERS: runner
}
__config__ = {
    'server': 'www.plantuml.com/plantuml',
    'https': True
}
__output__ = ['diagrams']
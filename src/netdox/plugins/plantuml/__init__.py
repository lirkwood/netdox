from netdox import Network, Node, Domain, IPv4Address 
from netdox.app import LifecycleStage
from netdox.plugins.plantuml.diagram import NodeDiagramFactory
from netdox.psml import image_fragment
from netdox.utils import config
from .diagram import OUTDIR

from shutil import rmtree
import os
import logging

logger = logging.getLogger(__name__)

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
        logger.debug(f'Drawing node diagram for: {node.name}')
        factory.draw(node)
        node.psmlFooter.insert(image_fragment('diagram', f'{diagram_dir}/{node.docid}.svg'))
    logger.debug('Finished drawing diagrams.')

__stages__ = {
    LifecycleStage.INIT: init,
    LifecycleStage.FOOTERS: runner
}
__config__ = {
    'server': 'www.plantuml.com/plantuml',
    'https': True
}
__output__ = ['diagrams']

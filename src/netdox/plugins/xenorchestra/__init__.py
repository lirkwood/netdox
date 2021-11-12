"""
Used to read and modify the VMs managed by Xen Orchestra
"""
from __future__ import annotations

import logging

from netdox import Network

logging.getLogger('websockets').setLevel(logging.INFO)

from netdox.plugins.xenorchestra.fetch import runner
from netdox.plugins.xenorchestra.objs import VirtualMachine
from netdox.plugins.xenorchestra.write import genpub, genreport

global pubdict
pubdict = {}
def nodes(network: Network) -> None:
    global pubdict
    pubdict = runner(network)

def _write(network: Network) -> None:
    genpub(network, pubdict)
    genreport(network)



__stages__ = {
    'nodes': nodes,
    'write': _write
}

__nodes__ = [VirtualMachine]
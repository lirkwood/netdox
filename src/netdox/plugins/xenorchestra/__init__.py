"""
Used to read and modify the VMs managed by Xen Orchestra
"""
from __future__ import annotations

import logging
import os

from netdox import Network
from netdox.utils import APPDIR

logging.getLogger('websockets').setLevel(logging.INFO)

from netdox.plugins.xenorchestra.fetch import runner
from netdox.plugins.xenorchestra.objs import VirtualMachine
from netdox.plugins.xenorchestra.write import genpub, genreport

global pubdict
pubdict: dict = {}
def nodes(network: Network) -> None:
    global pubdict
    pubdict = runner(network)

def _write(network: Network) -> None:
    genpub(network, pubdict)
    genreport(network)

def init():
    if not os.path.exists(APPDIR + 'plugins/xenorchestra/src'):
        os.mkdir(APPDIR + 'plugins/xenorchestra/src')

__stages__ = {
    'nodes': nodes,
    'write': _write
}

__nodes__ = [VirtualMachine]

__config__ = {
    'username': '',
    'password': '',
    'host': '',
}
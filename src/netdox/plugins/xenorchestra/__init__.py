"""
Used to read and modify the VMs managed by Xen Orchestra
"""
from __future__ import annotations

import logging
import os
from shutil import rmtree

from netdox import Network
from netdox.app import LifecycleStage
from netdox.utils import APPDIR

logging.getLogger('websockets').setLevel(logging.INFO)

from netdox.plugins.xenorchestra.fetch import runner
from netdox.plugins.xenorchestra.objs import VirtualMachine, Pool
from netdox.plugins.xenorchestra.write import genpub, genreport, write_backups, BACKUP_DIR

SRC_DIR = os.path.join(APPDIR, 'plugins/xenorchestra/src')

global pools
pools: list[Pool] = []
def nodes(network: Network) -> None:
    global pools
    pools = runner(network)

def write(network: Network) -> None:
    genpub(network, pools)
    genreport(network)
    write_backups(network)

def init(_: Network):
    if not os.path.exists(APPDIR + 'plugins/xenorchestra/src'):
        os.mkdir(APPDIR + 'plugins/xenorchestra/src')
        
    if os.path.exists(BACKUP_DIR):
        rmtree(BACKUP_DIR)
    os.mkdir(BACKUP_DIR)
__stages__ = {
    LifecycleStage.INIT: init,
    LifecycleStage.NODES: nodes,
    LifecycleStage.WRITE: write
}

__nodes__ = [VirtualMachine]

__output__ = ['xopub.psml', 'xobackup']

__config__ = {
    'username': '',
    'password': '',
    'host': '',
}
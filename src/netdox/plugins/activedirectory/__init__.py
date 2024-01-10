"""
Used to read and modify DNS records stored in ActiveDirectory.
"""

import logging

from netdox.app import LifecycleStage
from netdox.plugins.activedirectory.dns import fetchDNS
from netdox.plugins.activedirectory.footers import addFooters

logging.getLogger('pypsrp').setLevel(logging.WARNING)

__stages__ = {
    LifecycleStage.DNS: fetchDNS,
    LifecycleStage.FOOTERS: addFooters,
}

__config__ = {
    "server": '',
    "username": '',
    "password": ''
}

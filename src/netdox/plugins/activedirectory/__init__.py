"""
Used to read and modify DNS records stored in ActiveDirectory.
"""

from netdox.plugins.activedirectory.dns import fetchDNS
from netdox.plugins.activedirectory.footers import addFooters
import logging

logging.getLogger('pypsrp').setLevel(logging.WARNING)

__stages__ = {
    'dns': fetchDNS,
    'footers': addFooters,
}

__config__ = {
    "server": str,
    "username": str,
    "password": str
}
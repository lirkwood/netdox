"""
Used to read and modify DNS records stored in ActiveDirectory.

This plugin uses a shared storage location in order to pass information back and forth between the Netdox host and the ActiveDirectory DNS server.
"""

from netdox.plugins.activedirectory.dns import fetchDNS
from netdox.plugins.activedirectory.footers import addFooters

__stages__ = {
    'dns': fetchDNS,
    'footers': addFooters
}
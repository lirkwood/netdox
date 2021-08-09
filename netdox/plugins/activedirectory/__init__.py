"""
Used to read and modify DNS records stored in ActiveDirectory.

This plugin uses a shared storage location in order to pass information back and forth between the Netdox host and the ActiveDirectory DNS server.
"""

from networkobjs import Network
from plugins import BasePlugin as BasePlugin
from plugins.activedirectory.create import create_forward, create_reverse
from plugins.activedirectory.fetch import fetchDNS


class Plugin(BasePlugin):
    name = 'activedirectory'
    stages = ['dns']

    def runner(self, network: Network, *_) -> None:
        fetchDNS(network)

    def create_A(self, name: str, ip: str, zone: str):
        create_forward(name, ip, zone, 'A')

    def create_CNAME(self, name: str, value: str, zone: str):
        create_forward(name, value, zone, 'CNAME')

    def create_PTR(self, ip: str, value: str):
        create_reverse(ip, value)

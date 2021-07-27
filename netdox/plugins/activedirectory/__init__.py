"""
Used to read and modify DNS records stored in ActiveDirectory.

This plugin uses a shared storage location in order to pass information back and forth between the Netdox host and the ActiveDirectory DNS server.
"""
import os
import subprocess
from shutil import rmtree

from networkobjs import Network
from plugins import Plugin as BasePlugin
from plugins.activedirectory.create import create_forward, create_reverse
from plugins.activedirectory.fetch import fetchDNS


class Plugin(BasePlugin):
    name = 'activedirectory'
    stages = ['dns']

    def init(self) -> None:
        if os.path.exists('plugins/activedirectory/records'):
            rmtree('plugins/activedirectory/records')
        os.mkdir('plugins/activedirectory/records')

        for file in os.scandir('plugins/activedirectory/src'):
            if file.name.endswith('.bin'):
                subprocess.run(args = [
                    './crypto.sh',                                                          # executable
                    'decrypt',                                                              # method
                    'plugins/activedirectory/src/vector.txt',                               # IV path
                    file.path,                                                              # input path
                    f'plugins/activedirectory/records/{file.name.replace(".bin", ".json")}' # output path
                ])

    def runner(self, network: Network, *_) -> None:
        fetchDNS(network)

    def create_A(self, name: str, ip: str, zone: str):
        create_forward(name, ip, zone, 'A')

    def create_CNAME(self, name: str, value: str, zone: str):
        create_forward(name, value, zone, 'CNAME')

    def create_PTR(self, ip: str, value: str):
        create_reverse(ip, value)

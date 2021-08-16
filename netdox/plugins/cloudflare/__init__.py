"""
Used to read and modify DNS records stored in CloudFlare.
"""
from netdox.networkobjs import Network
from netdox.plugins import BasePlugin as BasePlugin
from netdox.plugins.cloudflare.fetch import main


class Plugin(BasePlugin):
    name = 'cloudflare'
    stages = ['dns']

    def init(self) -> None:
        pass

    def runner(self, network: Network, *_) -> None:
        main(network)
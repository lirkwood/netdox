"""
Used to read and modify DNS records stored in CloudFlare.
"""
from networkobjs import Network
from plugins import Plugin as BasePlugin
from plugins.cloudflare.fetch import main


class Plugin(BasePlugin):
    name = 'cloudflare'
    stages = ['dns']

    def init(self) -> None:
        pass

    def runner(self, network: Network, *_) -> None:
        main(network)
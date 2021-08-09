"""
Used to retrieve NAT information from FortiGate and pfSense
"""
from plugins.nat.fetch import runner
from plugins import BasePlugin as BasePlugin
from networkobjs import Network

class Plugin(BasePlugin):
    name = 'nat'
    stages = ['dns']

    def init(self) -> None:
        pass

    def runner(self, network: Network, *_) -> None:
        runner(network)
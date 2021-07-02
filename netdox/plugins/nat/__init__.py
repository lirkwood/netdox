"""
Used to retrieve NAT information from FortiGate and pfSense
"""
from plugins.nat.fetch import runner
from plugins import Plugin as BasePlugin
from networkobjs import Network

class Plugin(BasePlugin):
    name = 'nat'
    stage = 'dns'

    def init(self) -> None:
        pass

    def runner(self, network: Network) -> None:
        runner(network)
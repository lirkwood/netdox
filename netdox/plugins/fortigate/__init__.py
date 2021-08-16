"""
Used to retrieve NAT information from FortiGate.
"""
import re

from netdox import utils
from netdox.iptools import regex_ip
from netdox.networkobjs import IPv4Address, Network
from netdox.plugins import BasePlugin

patt_nat = re.compile(rf'(?P<alias>{regex_ip.pattern}).+?(?P<dest>{regex_ip.pattern}).*')

class Plugin(BasePlugin):
    name = 'fortigate'
    stages = ['nat']

    def runner(self, network: Network, stage: str) -> None:
        if stage == 'nat':
            with open(utils.APPDIR+ 'src/nat.txt','r') as stream:
                natDict = {}
                for line in stream.read().splitlines():
                    match = re.match(patt_nat, line)
                    if match:
                        natDict[match['alias']] = match['dest']
                        natDict[match['dest']] = match['alias']

            for ip in natDict:
                if ip not in network.ips:
                    IPv4Address(network, ip, True)
                network.ips[ip].nat = natDict[ip]

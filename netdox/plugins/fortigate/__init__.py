"""
Used to retrieve NAT information from FortiGate.
"""
import re

from netdox import utils
from netdox.iptools import regex_ip
from netdox.objs import IPv4Address, Network

patt_nat = re.compile(rf'(?P<alias>{regex_ip.pattern}).+?(?P<dest>{regex_ip.pattern}).*')

def runner(network: Network) -> None:
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

__stages__ = {'nat': runner}
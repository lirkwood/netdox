"""
Fetching data
*************
"""
import json
import re
import subprocess

import iptools
from networkobjs import IPv4Address, Network

patt_nat = re.compile(r'(?P<alias>(\d{1,3}\.){3}\d{1,3}).+?(?P<dest>(\d{1,3}\.){3}\d{1,3}).*')

def runner(network: Network):
    """
    Reads the NAT dump from FortiGate and calls the pfSense node script.

    :Args:
        forward_dns:
            A forward DNS set
    """
    # Gather FortiGate NAT
    with open('src/nat.txt','r') as stream:
        natDict = {}
        for line in stream.read().splitlines():
            match = re.match(patt_nat, line)
            if match:
                alias = iptools.ipv4(match['alias'])
                dest = iptools.ipv4(match['dest'])
                natDict[alias.ipv4] = dest.ipv4
                natDict[dest.ipv4] = alias.ipv4

    # Gather pfSense NAT
    pfsense = subprocess.check_output('node plugins/nat/pfsense.js', shell=True)
    natDict |= json.loads(pfsense)

    for ip in natDict:
        if ip not in network.ips:
            network.ips.add(IPv4Address(ip, True))
        network.ips[ip].nat = natDict[ip]

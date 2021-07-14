"""
Fetching data
*************
"""
import json
import re
import subprocess
from iptools import regex_ip

from networkobjs import IPv4Address, Network

patt_nat = re.compile(rf'(?P<alias>{regex_ip.pattern}).+?(?P<dest>{regex_ip.pattern}).*')

def runner(network: Network):
    """
    Reads the NAT dump from FortiGate and calls the pfSense node script.

    :param network: The network
    :type network: Network
    """
    # Gather FortiGate NAT
    with open('src/nat.txt','r') as stream:
        natDict = {}
        for line in stream.read().splitlines():
            match = re.match(patt_nat, line)
            if match:
                natDict[match['alias']] = match['dest']
                natDict[match['dest']] = match['alias']

    # Gather pfSense NAT
    pfsense = subprocess.check_output('node plugins/nat/pfsense.js', shell=True)
    natDict |= json.loads(pfsense)

    for ip in natDict:
        if ip not in network.ips:
            network.ips.add(IPv4Address(ip, True))
        network.ips[ip].nat = natDict[ip]

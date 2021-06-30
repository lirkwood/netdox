"""
Fetching data
*************
"""
import re, json, iptools, subprocess
from network import Network

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

    for ip in network.ips:
        if ip.addr in natDict:
            ip.nat = natDict[ip.addr]
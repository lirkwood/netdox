import json, re
import iptools

patt_nat = re.compile(r'(?P<alias>(\d{1,3}\.){3}\d{1,3}):\d+\s+(?P<dest1>(\d{1,3}\.){3}\d{1,3})-(?P<dest2>(\d{1,3}\.){3}\d{1,3}).*')

with open('nat.txt','r') as stream:
    natDict = {}
    for line in stream.read().splitlines():
        match = re.match(patt_nat, line)
        
        alias = iptools.parsed_ip(match['alias'])
        dest = iptools.parsed_ip(match['dest1'])
        if alias.ipv4 in natDict:
            print(f'[WARNING][nat.py] {alias.ipv4} has multiple destinations in the NAT ({dest.ipv4}, {natDict[alias.ipv4]}, ...?)')
            print(f'[INFO][nat.py] Defaulting to last discovered destination: {dest.ipv4}')
        natDict[alias.ipv4] = dest.ipv4

def lookup(ip):
    return natDict[ip]
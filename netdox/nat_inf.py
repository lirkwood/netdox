import re
import iptools

patt_nat = re.compile(r'(?P<alias>(\d{1,3}\.){3}\d{1,3}).+?(?P<dest>(\d{1,3}\.){3}\d{1,3}).*')

with open('src/nat.txt','r') as stream:
    natDict = {}
    for line in stream.read().splitlines():
        match = re.match(patt_nat, line)
        if match:
            alias = iptools.ipv4(match['alias'])
            dest = iptools.ipv4(match['dest'])
            natDict[alias.ipv4] = dest.ipv4
            natDict[dest.ipv4] = alias.ipv4

def lookup(ip):
    if ip in natDict:
        return natDict[ip]
    else:
        return None
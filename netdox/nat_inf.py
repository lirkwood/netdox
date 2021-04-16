import re, json, utils, iptools, subprocess

patt_nat = re.compile(r'(?P<alias>(\d{1,3}\.){3}\d{1,3}).+?(?P<dest>(\d{1,3}\.){3}\d{1,3}).*')

with open('src/nat.txt','r') as stream:
    global natDict
    natDict = {}
    for line in stream.read().splitlines():
        match = re.match(patt_nat, line)
        if match:
            alias = iptools.ipv4(match['alias'])
            dest = iptools.ipv4(match['dest'])
            natDict[alias.ipv4] = dest.ipv4
            natDict[dest.ipv4] = alias.ipv4

@utils.mod_set
def _pfsense(nat_set):
    jsondata = subprocess.check_output('node pfsense.js', shell=True)
    pf_nat = json.loads(jsondata)
    nat_set = pf_nat | nat_set
    return nat_set

def pfsense():
    global natDict
    natDict = _pfsense(natDict)

def lookup(ip):
    if ip in natDict:
        return natDict[ip]
    else:
        return None
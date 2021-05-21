import re, json, utils, iptools, subprocess

patt_nat = re.compile(r'(?P<alias>(\d{1,3}\.){3}\d{1,3}).+?(?P<dest>(\d{1,3}\.){3}\d{1,3}).*')

def runner(forward_dns: dict[str, utils.DNSRecord], reverse_dns: dict[str, utils.DNSRecord]):
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

    for domain in forward_dns:
        dns = forward_dns[domain]
        for ip in dns.ips:
            if ip in natDict:
                dns.link(natDict[ip], 'ipv4', 'NAT')
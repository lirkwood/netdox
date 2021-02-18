from bs4 import BeautifulSoup
import subprocess, json
import iptools
import nat

def main(ipdict, ptr):
    tmp = {}
    for ip in ipdict:
        _ip = iptools.parsed_ip(ip)
        if _ip.valid:
            if not _ip.public:
                for sibling in _ip.iter_subnet():
                    if sibling not in ipdict:
                        tmp[sibling] = {'source': 'Generated'}
    ipdict = tmp | ipdict   #populate ipdict with unused private ips

    for ip in ipdict:
        _ip = iptools.parsed_ip(ip)
        ipdict[ip]['nat'] = nat.lookup(ip)
        if ip in ptr:
            ipdict[ip]['ptr'] = ptr[ip]
        ipdict[ip]['subnet'] = _ip.subnet
        ipdict[ip]['o3'] = ip.split('.')[2]
        ipdict[ip]['o3-4'] = '.'.join(ip.split('.')[2:4])


    with open('src/nmap.xml', 'r') as stream:
        soup = BeautifulSoup(stream, features='xml')
        for port in soup.find_all('port'):
            ip = port.parent.parent.address['addr']
            if port.service:
                if 'ports' not in ipdict[ip]:
                    ipdict[ip]['ports'] = {}
                ipdict[ip]['ports'][port['portid']] = port.service['name']
    
    with open('src/ips.json','w') as output:
        output.write(json.dumps(ipdict, indent=2))
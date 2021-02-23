from bs4 import BeautifulSoup
import json
import iptools, nat

def main(ipdict, ptr):
    tmp = {}
    for ip in ipdict:
        _ip = iptools.parsed_ip(ip)
        if _ip.valid:
            if (not _ip.public) or _ip.in_subnet('103.127.18.0/24') or _ip.in_subnet('119.63.219.195/26'):
                for sibling in _ip.iter_subnet():
                    if sibling not in ipdict:
                        tmp[sibling] = {'source': 'Generated'}
    ipdict = tmp | ipdict   #populate ipdict with unused private ips

    for ip in ipdict:
        _ip = iptools.parsed_ip(ip)
        ipnat = nat.lookup(ip)
        if ipnat:
            ipdict[ip]['nat'] = ipnat
        if ip in ptr:
            ipdict[ip]['ptr'] = ptr[ip]
        ipdict[ip]['subnet'] = _ip.subnet
        ipdict[ip]['network'] = f'{_ip.octets[0]}.{_ip.octets[1]}.0.0/16'
        ipdict[ip]['for-search'] = f"{ip.split('.')[2]}, {'.'.join(ip.split('.')[2:4])}"

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
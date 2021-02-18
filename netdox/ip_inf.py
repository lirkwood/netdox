from bs4 import BeautifulSoup
import subprocess, json
import iptools

def main(ipdict, ptr):
    for ip in ipdict:
        if ip in ptr:
            ipdict[ip]['ptr'] = ptr[ip]

        ip = iptools.parsed_ip(ip)
        if ip.valid:
            if not ip.public:
                for sibling in ip.iter_subnet():
                    if sibling not in ipdict:
                        ipdict[sibling] = 'Generated'
                        
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
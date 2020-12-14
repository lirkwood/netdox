from bs4 import BeautifulSoup

def main():
    with open('../Sources/nmap.xml', 'r') as stream:
        soup = BeautifulSoup(stream, 'lxml')
        all = soup.find_all('port')
        d = {}
        for port in all:
            portid = port['portid']
            services = port.find_all('service')
            for s in services:
                service = s['name']
                if portid not in d:
                    d[portid] = [service]
                else:
                    if service not in d[portid]:
                        d[portid].append(service)
    d['8080'] = ['Kubernetes']
    write(d)
    unused(d)


def write(d):
    for portid in d:
        with open('../Sources/template-ports.psml', 'r') as stream:
            soup = BeautifulSoup(stream, features='xml')
            soup.uri['docid'] = '_nd_port_' + portid
            soup.uri['title'] = 'Port ' + portid
            soup.heading.string = 'Port ' + portid
            port = soup.find(title='Port Number')
            port['value'] = portid
            serfrag = soup.find(id='services')
            for service in d[portid]:
                p = soup.new_tag('property')
                p['name'] = 'service'
                p['title'] = 'Service'
                p['value'] = service
                serfrag.append(p)
            output = open('../Ports/port_{0}.psml'.format(portid), 'w')
            output.write(str(soup))

def unused(d):
    for i in range(256):
        portid = str(i)
        if portid not in d.keys():
            with open('../Sources/template-ports.psml', 'r') as stream:
                soup = BeautifulSoup(stream, features='xml')
                soup.uri['docid'] = '_nd_port_' + portid
                soup.uri['title'] = 'Port ' + portid
                soup.heading.string = 'Port ' + portid
                port = soup.find(title='Port Number')
                port['value'] = portid
                serfrag = soup.find(id='services')
                serfrag.decompose()
                output = open('../Ports/port_{0}.psml'.format(portid), 'w')
                output.write(str(soup))

if __name__ == '__main__':
    main()

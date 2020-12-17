from bs4 import BeautifulSoup
import csv
import pprint

def read():
    live = {}
    with open('../Sources/domains.csv', 'r') as stream:
        with open('../sources/nmap.xml', 'r') as n:
            soup = BeautifulSoup(n, 'lxml')
            ports = soup.find_all('ports') #find hosts that were checked for ports => live
            for p in ports:
                addrtag = p.parent.find('address', addrtype='ipv4')
                ip = addrtag['addr']
                live[ip] = 'nmap'
            for row in csv.reader(stream):
                for ip in row[2:]:
                    live[ip] = row[0]
        
    write(live)

def write(l):
    subnets = {}
    addrlist = []
    for ip in l:
        with open('../Sources/template-ip.psml', 'r') as template:
            with open('../sources/nmap.xml', 'r') as nstream:
                nmap = BeautifulSoup(nstream, features='xml')
                soup = BeautifulSoup(template, features='xml')     #open template as soup

                docid = '_nd_' + ip.replace('.', '_')
                network = '.'.join(ip.split('.')[:2]) #split it into components
                subnet = ip.split('.')[2]
                addr = ip.split('.')[3]

                allprops = soup.find_all('property')   #find all properties
                for p in allprops:
                    if p['name'] == 'network':  #populate properties
                        p['value'] = '{0}.0.0/16'.format(network)
                    elif p['name'] == 'subnet':
                        p['value'] = '{0}.{1}.0/24'.format(network, subnet)
                    elif p['name'] == 'ip':
                        p['value'] = ip + '/32'
                    elif p['name'] == 'source':
                        p['value'] = l[ip]

                soup.uri['docid'] = docid
                soup.uri['title'] = ip
                soup.heading.string = ip

                if network == '192.168':
                    portfrag = soup.find(id='ports') #find xref fragment
                    atags = nmap.find_all(addr=ip) #find all host blocks with matching ips
                    for t in atags:
                        h = t.parent
                        ports = h.find('ports')
                        if ports:    #if host block has ports
                            for port in ports.find_all('port'):
                                services = port.find_all('service')
                                if services:
                                    service = services[0]['name']
                                else:
                                    service = 'nothing'
                                p = soup.new_tag('property')
                                p['name'] = 'port'
                                p['title'] = service + ' port'
                                p['datatype'] = 'xref'
                                portfrag.append(p)
                                
                                x = soup.new_tag('xref')
                                x['frag'] = 'default'
                                x['docid'] = '_nd_port_' + port['portid']
                                x.string = 'Port ' + port['portid']
                                p.append(x)

                    if subnet not in subnets:
                        subnets[subnet] = []
                    if addr not in subnets[subnet]:
                        subnets[subnet].append(addr)
                elif network == '103.127' and subnet == '18':
                    addrlist.append(addr)

                

                labels(network, soup, 'live')
                output = open('../IPs/{0}.psml'.format(docid), 'w', encoding='utf-8')
                output.write(str(soup))

    unused(subnets, addrlist)

def unused(d, l):
    with open('../Sources/subnets.txt', 'w') as o:
        for k in d:     #for key in dictionary of subnets
            k = str(k)
            o.write('192.168.{0}.0/24\n'.format(k))
            for i in range(256):    #for every possible address in subnet
                i = str(i)
                if i not in d[k]:   #if has not been seen
                    writeDead('192.168', k, i)  #assume unused and gen doc
    for i in range(256):    #for all possible ips in 103.127.18 range
        i = str(i)
        if i not in l:  #if has not been seen
            writeDead('103.127', '18', i)
        
                    

def writeDead(network, subnet, addr):
    with open('../Sources/template-ip.psml', 'r') as template:
        soup = BeautifulSoup(template, features='xml')

        ip = network + '.' + subnet + '.' + addr
        docid = '_nd_' + ip.replace('.', '_')

        soup.uri['docid'] = docid
        soup.uri['title'] = ip
        soup.heading.string = ip
        
        allprops = soup.find_all('property')   #find all properties
        for p in allprops:
            if p['name'] == 'network':  #populate properties
                p['value'] = '{0}.0.0/16'.format(network)
            elif p['name'] == 'subnet':
                p['value'] = '{0}.{1}.0/24'.format(network, subnet)
            elif p['name'] == 'ip':
                p['value'] = ip
            elif p['name'] == 'source':
                p['value'] = 'Generated'

        # status = soup.new_tag('property')
        # status['name'] = 'status'
        # status['title'] = 'Status'
        # status['value'] = 'Address unused.'

        # portfrag = soup.find(id='ports')
        # portfrag.append(status)

        if network != '192.168':
            soup.find(title='Subnet')['value'] = '—'

        labels(network, soup, 'unused')
        output = open('../IPs/{0}.psml'.format(docid), 'w', encoding='utf-8')
        output.write(str(soup))


def labels(network, soup, status):
    label = soup.new_tag('labels')
    if network == '192.168' or network.startswith('172') or network.startswith('10.'):
        label.string = 'private'
    else:
        label.string = 'public'
        subntag = soup.find(title='Subnet')
        subntag['value'] = '—'
    if status == 'unused':
        label.string += ',unused'
    else:
        label.string += ',active'
    soup.uri.append(label)


if __name__ == '__main__':
    read()

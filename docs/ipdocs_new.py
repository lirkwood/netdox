from bs4 import BeautifulSoup
import binary
import pprint
import copy
import csv
import os


def main():
    if not os.path.exists('../IPs'):
        os.mkdir('../IPs')

    live = read()
    subndict = {}
    for ip in live:
        subnet = '.'.join(ip.split('.')[:3])
        if subnet not in subndict:
            subndict[subnet] = {}
        subndict[subnet][ip] = live[ip]
    
    dead = {}
    for subnet in subndict:
        if '192.168.' in subnet or '103.127.18' in subnet:
            for i in range(256):
                ip = subnet + '.' + str(i)
                if ip not in subndict[subnet]:
                    dead[ip] = 'Generated'
    
    ipdict = dead | live

    
    with open('../Sources/template-ip.psml', 'r') as template:
        with open('../sources/nmap.xml', 'r') as nstream:
            nmap = BeautifulSoup(nstream, features='xml')
            soup = BeautifulSoup(template, features='xml')     #open template as soup
            for ip in ipdict:
                print(ip)
                write(ip, ipdict[ip], nmap, soup)
        

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

    return live
    

def write(ip, source, nmap, soup):
    docid = '_nd_' + ip.replace('.', '_')
    network = '.'.join(ip.split('.')[:2]) #split it into components

    allprops = soup.find_all('property')   #find all properties
    for p in allprops:
        if p['name'] == 'network':  #populate properties
            p['value'] = '{0}.0.0/16'.format(network)
        elif p['name'] == 'subnet':
            p['value'] = binary.netbox_sort(ip)
        elif p['name'] == 'ipv4':
            p['value'] = ip
        elif p['name'] == 'source':
            p['value'] = source

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

    labels(soup)
    output = open('../IPs/{0}.psml'.format(docid), 'w', encoding='utf-8')
    output.write(str(soup))

def labels(soup):
    ip = soup.find(title='IP')['value']
    source = soup.find(title='Source')['value']

    label = soup.new_tag('labels')
    if ip.startswith('192.168.') or ip.startswith('172.') or ip.startswith('10.'):
        label.string = 'private'
    else:
        label.string = 'public'
    if source == 'Generated':
        label.string += ',unused'
    else:
        label.string += ',active'
    soup.uri.append(label)


if __name__ == '__main__':
    main()
from bs4 import BeautifulSoup
import iptools
import copy
import os


def main(iplist, ptr):

    live = read(iplist)
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
                    dead[ip] = {'source': 'Generated'}
    
    ipdict = dead | live
    with open('src/nmap.xml', 'r') as stream:
        soup = BeautifulSoup(stream, features='xml')
        for port in soup.find_all('port'):
            ip = port.parent.parent.address['addr']
            if port.service:
                if 'ports' not in ipdict[ip]:
                    ipdict[ip]['ports'] = {}
                ipdict[ip]['ports'][port['portid']] = port.service['name']
    
    with open('src/template-ip.psml', 'r') as template:
        soup = BeautifulSoup(template, features='xml')     #open template as soup
        for item in ipdict:
            ip = iptools.parsed_ip(item)
            if ip.valid:
                write(ip, ipdict[ip.ipv4], copy.copy(soup), ptr)
        

def read(iplist):
    live = {}
    with open('src/nmap.xml', 'r') as n:
        soup = BeautifulSoup(n, 'lxml')
        ports = soup.find_all('ports') #find hosts that were checked for ports => live
        for p in ports:
            addrtag = p.parent.find('address', addrtype='ipv4')
            ip = addrtag['addr']
            live[ip] = {}
            live[ip]['source'] = 'nmap'

    for ip in iplist:
        if ip not in live:
            live[ip] = {'source': iplist[ip]}

    return live
    

def write(ip, info, soup, ptr):
    docid = '_nd_' + ip.ipv4.replace('.', '_')
    network = '.'.join(ip.ipv4.split('.')[:2]) #split it into components

    allprops = soup.find_all('property')   #find all properties
    for p in allprops:
        if p['name'] == 'network':  #populate properties
            p['value'] = '{0}.0.0/16'.format(network)
        elif p['name'] == 'subnet':
            p['value'] = ip.subnet
        elif p['name'] == 'ipv4':
            p['value'] = ip.ipv4
        elif p['name'] == 'ipv4_3':
            p['value'] == ip.ipv4.split('.')[2]
        elif p['name'] == 'ipv4_3-4':
            p['value'] == ip.ipv4.split('.')[2:4]
        elif p['name'] == 'source':
            p['value'] = info['source']

    docinf = soup.new_tag('documentinfo')
    uri = soup.new_tag('uri')
    docinf.append(uri)
    soup.document.insert(0, docinf)
    uri['docid'] = docid
    uri['title'] = ip.ipv4
    soup.heading.string = ip.ipv4
    labels(soup)

    if 'ports' in info:
        portfrag = soup.find(id='ports')
        for port in info['ports']:
            service = info['ports'][port]
            p = soup.new_tag('property')
            p['name'] = 'port'
            p['title'] = service + ' port'
            p['datatype'] = 'xref'
            portfrag.append(p)
            
            x = soup.new_tag('xref')
            x['frag'] = 'default'
            x['docid'] = '_nd_port_' + port
            x.string = 'Port ' + port
            p.append(x)
    
    if ip.ipv4 in ptr:
        ptrsection = soup.find(id='reversedns')
        ptrsection['title'] = 'Reverse DNS'
        ptrfrag = soup.new_tag('properties-fragment')
        ptrfrag['id'] = 'ptr'
        ptrsection.append(ptrfrag)
        for domain in ptr[ip.ipv4]:
            p = soup.new_tag('property')
            p['name'] = 'domain'
            p['title'] = 'Domain'
            p['datatype'] = 'xref'

            x = soup.new_tag('xref')
            x['frag'] = 'default'
            x['docid'] = '_nd_'+ domain.replace('.','_')
            p.append(x)
            ptrfrag.append(p)

    output = open('out/IPs/{0}.psml'.format(docid), 'w', encoding='utf-8')
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
    label.string += ',show-reversexrefs'
    soup.uri.append(label)
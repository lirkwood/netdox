import os
import json
from bs4 import BeautifulSoup

def toJson():
    list = extract()
    aliases(list)

    with open('../Sources/ad.xml', 'w') as stream:
        soup = BeautifulSoup('', features='xml')

        root = soup.new_tag('root')
        soup.append(root)
        for item in list:
            record = soup.new_tag('record')
            root.append(record)
            hostname = soup.new_tag('hostname')
            hostname.string = item[0]
            network = soup.new_tag('network')
            network.string = item[1]
            subnet = soup.new_tag('subnet')
            subnet.string = item[2]
            addr = soup.new_tag('addr')
            addr.string = item[3]

            record.append(hostname)
            record.append(network)
            record.append(subnet)
            record.append(addr)

        stream.write(str(soup))


def extract():
    list = []

    for file in os.scandir("../Sources/records"):
        source = open(file, 'r')

        jsondata = json.load(source)    #load json file

        for record in jsondata:
            if record['RecordType'] == 'A': 
                hostnamestr = record['DistinguishedName'].split(',')    #get hostname
                subdomain = hostnamestr[0].replace('DC=', '') #extract subdomain
                domain = hostnamestr[1].replace('DC=', '')    #extract top level domain
                if subdomain == '@':
                    hostname = domain
                elif domain in subdomain:   #if subdomain superset of domain
                    hostname = subdomain
                else:
                    hostname = subdomain + '.' + domain #assemble full domain name

                for item in record['RecordData']['CimInstanceProperties']:
                    if item['Name'] == "IPv4Address":
                        ip = item['Value'].strip('.')

                network = '.'.join(ip.split('.')[:2])
                subnet = ip.split('.')[2]
                address = ip.split('.')[3]

                hostname = hostname.replace('www.', '')
                list.append([hostname, network, subnet, address])
    return list

def aliases(list):
    cnames = {}
    for file in os.scandir("../Sources/records"):
        source = open(file)
        jsondata = json.load(source)

        for record in jsondata:
            if record['RecordType'] == 'CNAME':
                domain = record['DistinguishedName'].split(',')[1].strip('DC=')
                subdomain = record['DistinguishedName'].split(',')[0].strip('DC=')
                
                if subdomain == '@':    #if wildcard subdomains
                    hostname = domain   #ignore
                elif domain in subdomain:   #if subdomain superset of domain
                    hostname = subdomain    #ignore domain
                else:
                    hostname = subdomain + '.' + domain #assemble full domain name
                
                alias = ''
                for item in record['RecordData']['CimInstanceProperties']:
                    if item['Name'] == "HostNameAlias":
                        alias = item['Value'].strip('.')

                for item in list:
                    if item[0] == alias:
                        if alias not in cnames:
                            cnames[alias] = []
                        if hostname not in cnames[alias]:
                            cnames[alias].append(hostname)
    with open('../sources/cnames.json', 'w') as stream:
        stream.write(json.dumps(cnames, indent=4))

if __name__ == '__main__':
    toJson()
    

import os
import json
from bs4 import BeautifulSoup

def toJson():
    list = extract()

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
            # if record['RecordType'] == 'PTR':
            #     hostname = record['RecordData']['CimInstanceProperties'].split('"')[1].strip('.')
            #     ipbase = record['DistinguishedName'].split('DC=')[2].split('.')
            #     iptail = record['DistinguishedName'].split('DC=')[1]
            #     ip = '.'.join([ipbase[2], ipbase[1], ipbase[0], iptail]).strip(',')
            #     network = '.'.join(ip.split('.')[:2])
            #     subnet = ip.split('.')[2]
            #     address = ip.split('.')[3]

            #     hostname = hostname.strip('*.')
            #     hostname = hostname.strip('www.')
            #     list.append([hostname, network, subnet, address])
                
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
                        ip = item['Value']

                network = '.'.join(ip.split('.')[:2])
                subnet = ip.split('.')[2]
                address = ip.split('.')[3]

                hostname = hostname.replace('www.', '')
                list.append([hostname, network, subnet, address])
    return aliases(list)

def aliases(list):
    new = []

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
                    if item['Name'] == "IPv4Address":
                        alias = item['Value']

                for item in list:
                    if item[0] == alias:
                        new.append([hostname, item[1], item[2], item[3]])
    return list + new

if __name__ == '__main__':
    toJson()
    

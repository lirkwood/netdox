import os
import json
import iptools
from bs4 import BeautifulSoup

def main():
    path = "src/records"
    master = extract(path)
    return master


def extract(path):
    master = {'forward': {}, 'reverse': {}}
    forward = master['forward']
    reverse = master['reverse']
    for file in os.scandir(path):
        source = open(file, 'r')
        jsondata = json.load(source)    #load json file
        for record in jsondata:
            if record['RecordType'] == 'A': 
                hostnamestr = record['DistinguishedName'].split(',')    #get hostname
                subdomain = hostnamestr[0].replace('DC=', '') #extract subdomain
                domain = hostnamestr[1].replace('DC=', '')    #extract top level domain
                if subdomain == '@':
                    hostname = domain
                elif domain in subdomain:
                    hostname = subdomain
                else:
                    hostname = subdomain + '.' + domain

                hostname = hostname.replace('*.','_wildcard_')

                for item in record['RecordData']['CimInstanceProperties']:
                    if item['Name'] == "IPv4Address":
                        ip = item['Value'].strip('.')

                if hostname not in forward:
                    forward[hostname] = {'dest': {'ips': [], 'domains': [], 'apps': []}, 'root': domain, 'source': 'ActiveDirectory'}
                forward[hostname]['dest']['ips'].append(ip)

            elif record['RecordType'] == 'CNAME':
                domain = record['DistinguishedName'].split(',')[1].strip('DC=')
                subdomain = record['DistinguishedName'].split(',')[0].strip('DC=')
                
                if subdomain == '@':
                    hostname = domain
                elif subdomain == '*.':
                    hostname = '_wildcard_.'+ domain
                else:
                    hostname = subdomain +'.'+ domain
                
                dest = ''
                for item in record['RecordData']['CimInstanceProperties']:
                    if item['Name'] == "HostNameAlias":
                        dest = item['Value']
                        if not dest.endswith('.'):
                            dest += '.'+ domain
                        else:
                            dest = dest.strip('.')
            
                if hostname not in forward:
                    forward[hostname] = {'dest': {'ips': [], 'domains': [], 'apps': []}, 'root': domain, 'source': 'ActiveDirectory'}
                forward[hostname]['dest']['domains'].append(dest)
            
            elif record['RecordType'] == 'PTR':
                zone = record['DistinguishedName'].split(',')[1].strip('DC=')
                subnet = '.'.join(zone.replace('.in-addr.arpa','').split('.')[::-1])    #strip '.in-addr.arpa' and fix...
                address = record['DistinguishedName'].split(',')[0].strip('DC=')        #... backwards subnet.
                ip = iptools.parsed_ip(subnet +'.'+ address)

                for item in record['RecordData']['CimInstanceProperties']:
                    if item['Name'] == 'PtrDomainName':
                        dest = item['Value'].strip('.')

                if ip.valid:
                    if ip.ipv4 not in reverse:
                        reverse[ip.ipv4] = []
                    reverse[ip.ipv4].append(dest)


    return master


if __name__ == '__main__':
    main()
    

import os
import json
from bs4 import BeautifulSoup

def main():
    path = "../Sources/records"
    master = extract(path)
    aliases(master, path)
    return master


def extract(path):
    master = {}
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
                elif subdomain == '*.':
                    hostname = '_wildcard_.'+ domain
                else:
                    hostname = subdomain + '.' + domain

                for item in record['RecordData']['CimInstanceProperties']:
                    if item['Name'] == "IPv4Address":
                        ip = item['Value'].strip('.')

                if hostname not in master:
                    master[hostname] = {'aliases': [], 'ips': [], 'root': domain, 'source': 'ActiveDirectory'}
                master[hostname]['ips'].append(ip)
    return master

def aliases(master, path):
    for file in os.scandir(path):
        source = open(file)
        jsondata = json.load(source)

        for record in jsondata:
            if record['RecordType'] == 'CNAME':
                domain = record['DistinguishedName'].split(',')[1].strip('DC=')
                subdomain = record['DistinguishedName'].split(',')[0].strip('DC=')
                
                if subdomain == '@':
                    alias = domain
                elif subdomain == '*.':
                    alias = '_wildcard_.'+ domain
                else:
                    alias = subdomain +'.'+ domain
                
                dest = ''
                for item in record['RecordData']['CimInstanceProperties']:
                    if item['Name'] == "HostNameAlias":
                        dest = item['Value']
                        if not dest.endswith('.'):
                            dest += '.'+ domain
                        else:
                            dest = dest.strip('.')
            
                if dest not in master:
                    master[dest] = {'aliases': [], 'ips': [], 'root': domain, 'source': 'ActiveDirectory'}
                master[dest]['aliases'].append(alias)

                

if __name__ == '__main__':
    main()
    

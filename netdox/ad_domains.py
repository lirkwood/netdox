import os
import json
import iptools
import utils

def main():
    path = "src/records/"
    master = extract(path)
    return master


def extract(path):
    forward = {}
    reverse = {}
    for file in os.scandir(path):
        if file.name.endswith('.json'):
            try:
                with open(file,'r') as source:
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
                                forward[hostname] = utils.dns(hostname, source='ActiveDirectory', root=domain)
                            forward[hostname].link(ip, 'ipv4')

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
                                forward[hostname] = utils.dns(hostname, source='ActiveDirectory', root=domain)
                            forward[hostname].link(dest, 'domain')
                        
                        elif record['RecordType'] == 'PTR':
                            zone = record['DistinguishedName'].split(',')[1].strip('DC=')
                            subnet = '.'.join(zone.replace('.in-addr.arpa','').split('.')[::-1])    #strip '.in-addr.arpa' and fix...
                            address = record['DistinguishedName'].split(',')[0].strip('DC=')        #... backwards subnet.
                            ip = iptools.ipv4(subnet +'.'+ address)

                            for item in record['RecordData']['CimInstanceProperties']:
                                if item['Name'] == 'PtrDomainName':
                                    dest = item['Value'].strip('.')

                            if ip.valid:
                                if ip.ipv4 not in reverse:
                                    reverse[ip.ipv4] = []
                                reverse[ip.ipv4].append(dest)
            except Exception as e:
                print(f'[ERROR][ad_domains.py] Failed to parse file as json: {file.name}. Exception:')
                print(e)
                print('[ERROR][ad_domains.py] ****END****')
    return (forward, reverse)


if __name__ == '__main__':
    main()
    

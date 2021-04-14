from json.decoder import JSONDecodeError
import os
import json
import iptools
import utils

@utils.critical
def main():
    forward = {}
    reverse = {}
    for file in fetchJson():
        with open(file, 'r') as stream:
            try:
                jsondata = json.load(stream)
            except JSONDecodeError:
                print(f'[ERROR][ad_domains.py] Failed to parse file as json: {file.name}')
            else:
                _forward, _reverse = extract(jsondata)

def fetchJson():
    for file in os.scandir("src/records/"):
        if file.name.endswith('.json'):
            yield file

@utils.critical
def extract(jsondata):
    forward = {}
    reverse = {}
    for record in jsondata:
        if record['RecordType'] == 'A':

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
    return (forward, reverse)

def add_A(record, dns_set): 
    hostnamestr = record['DistinguishedName'].split(',')    #get hostname
    subdomain = hostnamestr[0].replace('DC=', '') #extract subdomain
    root = hostnamestr[1].replace('DC=', '')    #extract root domain

    # combine subdomain and root into fqdn
    if subdomain == '@':
        fqdn = root
    elif subdomain == '*':
        fqdn = '_wildcard_.' + root
    elif root in subdomain:
        fqdn = subdomain
    else:
        fqdn = subdomain + '.' + root

    for item in record['RecordData']['CimInstanceProperties']:
        if item['Name'] == "IPv4Address":
            ip = item['Value'].strip('.')

    if fqdn not in dns_set:
        dns_set[fqdn] = utils.dns(fqdn, source='ActiveDirectory', root=root)
    dns_set[fqdn].link(ip, 'ipv4')


if __name__ == '__main__':
    main()
    

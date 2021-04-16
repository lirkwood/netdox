from json.decoder import JSONDecodeError
import os, json
import iptools, utils

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
                forward = _forward | forward
                reverse = _reverse | reverse
    
    return (forward, reverse)


def fetchJson():
    for file in os.scandir("src/records/"):
        if file.name.endswith('.json'):
            yield file


def extract(jsondata):
    forward = {}
    reverse = {}
    for record in jsondata:
        if record['RecordType'] == 'A':
            forward = add_A(record, forward)

        elif record['RecordType'] == 'CNAME':
            forward = add_CNAME(record, forward)
        
        elif record['RecordType'] == 'PTR':
            reverse = add_PTR(record, reverse)
    return (forward, reverse)


def add_A(record, dns_set): 
    # Get name
    distinguished_name = record['DistinguishedName'].split(',')    #get hostname
    subdomain = distinguished_name[0].replace('DC=', '') #extract subdomain
    root = distinguished_name[1].replace('DC=', '')    #extract root domain
    fqdn = assemble_fqdn(subdomain, root)

    # Get value
    for item in record['RecordData']['CimInstanceProperties']:
        if item['Name'] == "IPv4Address":
            dest = item['Value'].strip('.')

    # Integrate
    if fqdn not in dns_set:
        dns_set[fqdn] = utils.dns(fqdn, source='ActiveDirectory', root=root)
    dns_set[fqdn].link(dest, 'ipv4')

    return dns_set

def add_CNAME(record, dns_set):
    distinguished_name = record['DistinguishedName'].split(',')
    subdomain = distinguished_name[0].strip('DC=')
    root = distinguished_name[1].strip('DC=')
    fqdn = assemble_fqdn(subdomain, root)
    
    for item in record['RecordData']['CimInstanceProperties']:
        if item['Name'] == "HostNameAlias":
            dest = item['Value']
            if not dest.endswith('.'):
                dest += '.'+ root
            else:
                dest = dest.strip('.')

    if fqdn not in dns_set:
        dns_set[fqdn] = utils.dns(fqdn, source='ActiveDirectory', root=root)
    dns_set[fqdn].link(dest, 'domain')

    return dns_set

def add_PTR(record, dns_set):
    zone = record['DistinguishedName'].split(',')[1].strip('DC=')
    subnet = '.'.join(zone.replace('.in-addr.arpa','').split('.')[::-1])    #strip '.in-addr.arpa' and reverse octet order
    address = record['DistinguishedName'].split(',')[0].strip('DC=')        #... backwards subnet.
    ip = iptools.ipv4(subnet +'.'+ address)

    for item in record['RecordData']['CimInstanceProperties']:
        if item['Name'] == 'PtrDomainName':
            dest = item['Value'].strip('.')

    if ip.valid:
        if ip.ipv4 not in dns_set:
            dns_set[ip.ipv4] = []
        dns_set[ip.ipv4].append(dest)
    
    return dns_set


def assemble_fqdn(subdomain, root):
    if subdomain == '@':
        fqdn = root
    elif subdomain == '*':
        fqdn = '_wildcard_.' + root
    elif root in subdomain:
        fqdn = subdomain
    else:
        fqdn = subdomain + '.' + root
    return fqdn


if __name__ == '__main__':
    main()
    

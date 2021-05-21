import os, re, json, subprocess
import iptools, utils

def fetchDNS(forward: dict[str, utils.DNSRecord], reverse: dict[str, utils.DNSRecord]):
    """
	Returns tuple containing forward and reverse DNS records from ActiveDirectory
    """
    for file in fetchJson():
        with open(file, 'r') as stream:
            try:
                jsondata = json.load(stream)
            except json.decoder.JSONDecodeError:
                print(f'[ERROR][ad_domains.py] Failed to parse file as json: {file.name}')
            else:
                for record in jsondata:
                    if record['RecordType'] == 'A':
                        add_A(forward, record)

                    elif record['RecordType'] == 'CNAME':
                        add_CNAME(forward, record)
                    
                    elif record['RecordType'] == 'PTR':
                        add_PTR(reverse, record)


def fetchJson() -> os.DirEntry:
    """
    Generator which yields a json file containing some DNS records
    """
    for file in os.scandir("plugins/activedirectory/records/"):
        if file.name.endswith('.json'):
            yield file


@utils.handle
def add_A(dns_set: dict[str, utils.DNSRecord], record: dict):
    """
	Integrates one A record into a dns set from json returned by AD api
    """
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
        dns_set[fqdn] = utils.DNSRecord(fqdn, source='ActiveDirectory', root=root)
    dns_set[fqdn].link(dest, 'ipv4')


@utils.handle
def add_CNAME(dns_set: dict[str, utils.DNSRecord], record: dict):
    """
	Integrates one CNAME record into a dns set from json returned by AD api
    """
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
        dns_set[fqdn] = utils.DNSRecord(fqdn, source='ActiveDirectory', root=root)
    dns_set[fqdn].link(dest, 'domain')


@utils.handle
def add_PTR(dns_set: dict[str, utils.DNSRecord], record: dict):
    """
	Integrates one PTR record into a dns set from json returned by AD api
    """
    zone = record['DistinguishedName'].split(',')[1].strip('DC=')
    subnet = '.'.join(zone.replace('.in-addr.arpa','').split('.')[::-1])    #strip '.in-addr.arpa' and reverse octet order
    address = record['DistinguishedName'].split(',')[0].strip('DC=')        #... backwards subnet.
    ip = iptools.ipv4(subnet +'.'+ address)

    for item in record['RecordData']['CimInstanceProperties']:
        if item['Name'] == 'PtrDomainName':
            dest = item['Value'].strip('.')

    if ip.valid:
        if ip.ipv4 not in dns_set:
            dns_set[ip.ipv4] = utils.PTRRecord(ip.ipv4, source='ActiveDirectory', root=zone)
        dns_set[ip.ipv4].link(dest)


def assemble_fqdn(subdomain: str, root: str) -> str:
    if subdomain == '@':
        fqdn = root
    elif subdomain == '*':
        fqdn = '_wildcard_.' + root
    elif root in subdomain:
        fqdn = subdomain
    else:
        fqdn = subdomain + '.' + root
    return fqdn.lower()


def create_forward(name: str, ip: str, zone: str, type: str):
    """
    Schedules a DNS record for creation in ActiveDirectory
    """
    if re.fullmatch(utils.dns_name_pattern, name) and iptools.valid_ip(ip):
        with open('src/dns.json', 'r') as dnsstream:
            dns = json.load(dnsstream)
            if ip in dns[name]['private_ips']:
                return None
        try:
            subprocess.check_call('./crypto.sh decrypt plugins/activedirectory/nfs/vector.txt plugins/activedirectory/nfs/scheduled.bin plugins/activedirectory/src/scheduled.json', shell=True)
            with open('plugins/activedirectory/src/scheduled.json', 'r') as stream:
                existing = json.load(stream)
        except subprocess.CalledProcessError:
            existing = []
        finally:
            new = {
                "name": name,
                "value": ip,
                "zone": zone,
                "type": type
            }
            existing.append(new)
            with open('plugins/activedirectory/src/scheduled.json', 'w') as stream:
                stream.write(json.dumps(existing))
            # subprocess.run('./crypto.sh encrypt plugins/activedirectory/nfs/vector.txt plugins/activedirectory/src/scheduled.json plugins/activedirectory/nfs/scheduled.bin', shell=True)
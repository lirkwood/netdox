"""
Creating Records
****************

Provides some functions for creating DNS records in ActiveDirectory
"""
import re, json, subprocess
import utils, iptools


def create_forward(name: str, ip: str, zone: str, type: str):
    """
    Schedules a forward DNS record for creation in ActiveDirectory

    :Args:
        name: str
            Name for the DNS record
        ip: str
            IPv4 address / domain for the record to resolve to
        zone: str
            DNS zone to create the record in
        type: str
            DNS Record type (A/CNAME)
    """
    if re.fullmatch(utils.dns_name_pattern, name) and iptools.valid_ip(ip):
        with open('src/forward.json') as stream:
            dns = utils.DNSSet.from_json(stream.read())
        if (ip, 'ActiveDirectory') in dns[name]._ips:
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

def create_reverse(ip: str, value: str):
    """
    Schedules a reverse DNS record for creation in ActiveDirectory

    :Args:
        ip: str
            IPv4 address to use as the name for the record
        value: str
            Domain for this record to resolve to
    """
    if iptools.valid_ip(ip) and re.fullmatch(utils.dns_name_pattern, value):
        with open('src/reverse.json', 'r') as dnsstream:
            dns = utils.DNSSet.from_json(dnsstream.read())
            if (value, 'ActiveDirectory') in dns[ip]._ptr:
                return None
    
        addr = ip.split('.')[-1]
        zone = f'{".".join(ip.split(".")[-2::-1])}.in-addr.arpa'
        try:
            subprocess.check_call('./crypto.sh decrypt plugins/activedirectory/nfs/vector.txt plugins/activedirectory/nfs/scheduled.bin plugins/activedirectory/src/scheduled.json', shell=True)
            with open('plugins/activedirectory/src/scheduled.json', 'r') as stream:
                existing = json.load(stream)
        except subprocess.CalledProcessError:
            existing = []
        finally:
            new = {
                "name": addr,
                "value": value,
                "zone": zone,
                "type": "PTR"
            }
            existing.append(new)
            with open('plugins/activedirectory/src/scheduled.json', 'w') as stream:
                stream.write(json.dumps(existing))
            # subprocess.run('./crypto.sh encrypt plugins/activedirectory/nfs/vector.txt plugins/activedirectory/src/scheduled.json plugins/activedirectory/nfs/scheduled.bin', shell=True)
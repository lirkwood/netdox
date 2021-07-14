"""
Creating Records
****************

Provides some functions for creating DNS records in ActiveDirectory.
"""
import re, json, subprocess
import networkobjs
import utils, iptools


def create_forward(name: str, value: str, zone: str, type: str) -> None:
    """
    Schedules a forward DNS record for creation in ActiveDirectory.

    :param name: The name for the record.
    :type name: str
    :param ip: The value for the record.
    :type ip: str
    :param zone: The DNS zone to create the record in.
    :type zone: str
    :param type: The type of record to create.
    :type type: str
    """
    if  re.fullmatch(networkobjs.dns_name_pattern, name) and (
        iptools.valid_ip(value) or re.fullmatch(networkobjs.dns_name_pattern, value)):

        with open('src/domains.json') as stream:
            domains = networkobjs.DomainSet.from_json(stream.read())
        if (value, 'ActiveDirectory') in (domains[name]._ips + domains[name]._cnames):
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
                "value": value,
                "zone": zone,
                "type": type
            }
            existing.append(new)
            with open('plugins/activedirectory/src/scheduled.json', 'w') as stream:
                stream.write(json.dumps(existing))
            # subprocess.run('./crypto.sh encrypt plugins/activedirectory/nfs/vector.txt plugins/activedirectory/src/scheduled.json plugins/activedirectory/nfs/scheduled.bin', shell=True)

def create_reverse(ip: str, value: str) -> None:
    """
    Schedules a reverse DNS record for creation in ActiveDirectory

    :param ip: The ip to use as the name of the record.
    :type ip: str
    :param value: The value for the record.
    :type value: str
    """
    if iptools.valid_ip(ip) and re.fullmatch(networkobjs.dns_name_pattern, value):
        
        with open('src/ips.json') as stream:
            ips = networkobjs.DomainSet.from_json(stream.read())
        if (value, 'ActiveDirectory') in ips[ip]._ptr:
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
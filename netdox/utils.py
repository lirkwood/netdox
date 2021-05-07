from typing import Iterable
import iptools, json, re
from traceback import format_exc
from datetime import datetime
from sys import argv

with open('src/authentication.json', 'r') as stream:
    global auth
    auth = json.load(stream)
    

try:
    with open('src/locations.json', 'r') as stream:
        _location_map = json.load(stream)
except Exception as e:
    print('[WARNING][utils.py] Unable to find or parse locations.json')
    _location_map = {}

location_map = {}
for location in _location_map:
    for subnet in _location_map[location]:
        location_map[subnet] = location

def locate(ip_set):
    if isinstance(ip_set, iptools.ipv4):
        if ip_set.valid:
            ip_set = [ip_set.ipv4]
        else:
            raise ValueError(f'Invalid IP in set: {ip_set.raw}')
    elif isinstance(ip_set, str):
        if iptools.valid_ip(ip_set):
            ip_set = [ip_set]
        else:
            raise ValueError(f'Invalid IP in set: {ip_set}')
    elif isinstance(ip_set, Iterable):
        for ip in ip_set:
            if not iptools.valid_ip(ip):
                raise ValueError(f'Invalid IP in set: {ip}')

    # sort every declared subnet that matches one of ips by mask size
    matches = {}
    for subnet in ip_set:
        for match in location_map:
            if iptools.subn_contains(match, subnet):
                mask = int(match.split('/')[-1])
                if mask not in matches:
                    matches[mask] = []
                matches[mask].append(location_map[match])

    matches = dict(sorted(matches.items(), reverse=True))

    # first key when keys are sorted by descending size is largest mask
    try:
        largest = matches[list(matches.keys())[0]]
        largest = list(dict.fromkeys(largest))
        # if multiple unique locations given by equally specific subnets
        if len(largest) > 1:
            return None
        else:
            # use most specific match for location definition
            return largest[0]
    # if no subnets
    except IndexError:
        return None



dns_name_pattern = re.compile(r'([a-zA-Z0-9_-]+\.)+[a-zA-Z0-9_-]+')

class dns:
    name: str
    root: str
    source: str
    location: str

    """
    Class representing some DNS record
    """

    def __init__(self, name, root=None, source=None):
        if re.fullmatch('([a-zA-Z0-9_-]+\.)+[a-zA-Z0-9_-]+', name):
            self.name = name.lower()
            if root: self.root = root.lower()
            self.source = source
            self.location = None
            self.icinga = {}
            self.role = None

            # destinations
            self.public_ips = set()
            self.private_ips = set()
            self.cnames = set()
            self.vms = set()
            self.apps = set()
            self.ec2s = set()

            self.subnets = set()
        else:
            raise ValueError('Must provide a valid name for dns record (some FQDN)')

    # switch to case match on 2021-04-10
    def link(self, string, type):
        """
        Adds a link to the given object.
        """
        if isinstance(string, str):
            string = string.lower().strip()
            if type == 'ipv4' or type == 'ip':
                if iptools.valid_ip(string):
                    if iptools.public_ip(string):
                        self.public_ips.add(string)
                    else:
                        self.private_ips.add(string)
                else:
                    raise ValueError(f'"{string}" is not a valid ipv4 address.')

            elif type == 'domain':
                if re.fullmatch(dns_name_pattern, string):
                    self.cnames.add(string)
                else:
                    raise ValueError(f'Domain {string} is not valid.')
            
            elif type == 'vm':
                self.vms.add(string)
            
            elif type == 'app':
                self.apps.add(string)

            elif type == 'ec2':
                self.ec2s.add(string)

            else:
                raise ValueError('Provide a valid destination type. One of: "ipv4", "domain", "vm", or "app".')
            
            self.update()

        else:
            raise TypeError('DNS destination must be provided as string')

    @property
    def destinations(self):
        return {
            'public_ips': self.public_ips,
            'private_ips': self.private_ips,
            'domains': self.domains,
            'vms': self.vms,
            'apps': self.apps,
            'ec2s': self.ec2s
        }

    @property
    def ips(self):
        return self.public_ips.union(self.private_ips)

    def update(self):
        for ip in self.private_ips:
            self.subnets.add(iptools.sort(ip))
        self.location = locate(self.private_ips)


class ptr:
    ipv4: str
    name: str
    subnet: str
    root: str
    source: str
    location: str
    unused: bool
    nat: str

    def __init__(self, ip, root=None, source=None, unused=False):
        if iptools.valid_ip(ip):
            self.ipv4 = ip
            self.name = ip
            self.subnet = iptools.sort(ip)
            if root: self.root = root.lower()
            self.source = source
            self.unused = unused
            self.location = locate(self.ipv4)

            self.ptrs = set()
            self.nat = None
        else:
            raise ValueError('Must provide a valid name for ptr record (some IPv4)')

    def link(self, name):
        if re.fullmatch(dns_name_pattern, name):
            self.ptrs.add(name)



def merge_sets(dns1,dns2):
    """
    Simple merge of any sets of found in two dns objects
    """
    if isinstance(dns1, dns) and isinstance(dns2, dns):
        dns1_inf = dns1.__dict__
        dns2_inf = dns2.__dict__
        for attr in dns2_inf:
            if isinstance(dns2_inf[attr], set):
                dns1_inf[attr] = dns1_inf[attr].union(dns2_inf[attr])
        return dns1
    else:
        raise TypeError(f'Arguments must be dns objects, not {type(dns1)}, {type(dns2)}')


class JSONEncoder(json.JSONEncoder):
    """
    Default json encoder except set type is encoded as sorted list
    """
    def default(self, obj):
        if isinstance(obj, dns) or isinstance(obj, ptr):
            return obj.__dict__
        elif isinstance(obj, set):
            return sorted(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


def critical(func):
    """
    For functions which are absolutely necessary. On fatal, entire app stops.
    """
    funcname = func.__name__
    funcmodule = func.__module__
    if funcmodule == '__main__':
        funcmodule = argv[0].replace('.py','')
    def wrapper(*args, **kwargs):
        print(f'[DEBUG][utils] [{datetime.now()}] Function {funcmodule}.{funcname} was called')
        try:
            returned = func(*args, **kwargs)
        except Exception as e:
            print(f'[ERROR][utils] Essential function {funcmodule}.{funcname} threw an exception:\n')
            raise e
        else:
            print(f'[DEBUG][utils] [{datetime.now()}] Function {funcmodule}.{funcname} returned')
            return returned
    return wrapper

def handle(func):
    """
    For functions that are not necessary. On fatal, return None and continue.
    """
    funcname = func.__name__
    funcmodule = func.__module__
    if funcmodule == '__main__':
        funcmodule = argv[0].replace('.py','')
    def wrapper(*args, **kwargs):
        try:
            returned = func(*args, **kwargs)
        except Exception:
            print(f'[WARNING][utils] Function {funcmodule}.{funcname} threw an exception:\n {format_exc()}')
            return None
        else:
            return returned
    return wrapper


@critical
def loadConfig():
    global config
    try:
        with open('src/config.json', 'r') as stream:
            config = json.load(stream)
    except FileNotFoundError:
        config = {'exclusions': []}
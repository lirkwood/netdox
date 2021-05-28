"""
This module contains any multi-purpose or generic code for use by both internal processes and plugins.

This script is mostly to improve the development process and encourage code reuse. 
It contains the two main classes used within Netdox, *DNSRecord* and *PTRRecord*, which represent all the DNS records which share a name.
It also defines two decorators which are used throughout Netdox, and some other functions which became useful across multiple scripts.
"""

from collections import defaultdict
import iptools, json, re
import subprocess
from typing import Iterable, Tuple, Union
from os import scandir, DirEntry
from traceback import format_exc
from datetime import datetime
from functools import wraps
from sys import argv

## Global vars
global authdict
def auth():
    """
    Returns the contents of the main configuration file, ``authentication.json``.
    If the file has not yet been opened in this instance, it is opened and read first.

    :Returns:
        A dictionary containing the authentication/configuration details for PageSeeder and any plugins which use it.
    """
    try:
        return authdict
    except NameError:
        with open('src/authentication.json', 'r') as stream:
            authdict = json.load(stream)
        return authdict

dns_name_pattern = re.compile(r'([a-zA-Z0-9_-]+\.)+[a-zA-Z0-9_-]+')

##############
# Decorators #
##############

def critical(func):
    """
    Prints timestamped debug messages before and after running the passed function.
    Also prints an additional message for clarity if the function raises an exception.
    """
    funcname = func.__name__
    funcmodule = func.__module__
    if funcmodule == '__main__':
        funcmodule = argv[0].replace('.py','')

    @wraps(func)
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
    Catches any exceptions raised by the passed function, prints the traceback, and returns *None*.
    Useful for functions which perform non-essential operations.
    """
    funcname = func.__name__
    funcmodule = func.__module__
    if funcmodule == '__main__':
        funcmodule = argv[0].replace('.py','')
        
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            returned = func(*args, **kwargs)
        except Exception:
            print(f'[WARNING][utils] Function {funcmodule}.{funcname} threw an exception:\n {format_exc()}')
            return None
        else:
            return returned
    return wrapper

############################
# Location helper function #
############################

try:
    with open('src/locations.json', 'r') as stream:
        _location_map = json.load(stream)
except Exception as e:
    print('[WARNING][utils] Unable to find or parse locations.json')
    _location_map = {}

location_map = {}
for location in _location_map:
    for subnet in _location_map[location]:
        location_map[subnet] = location

def locate(ip_set: Union[iptools.ipv4, str, Iterable]) -> str:
    """
    Returns a location for an ip or set of ips, or None if there is no determinable location.
    Locations are decided based on the content of the ``locations.json`` config file (for more see :ref:`config`)

    :Returns:
        String|None; A string containing the location as it appears in ``locations.json``, or None if no valid location could be decided on.
    """
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

###########
# Classes #
###########

class DNSRecord:
    """
    Forward DNS record
    """
    name: str
    root: str
    location: str

    def __init__(self, name: str=None, root: str=None, constructor: dict=None):
        if constructor:
            for k, v in constructor.items():
                setattr(self, k, v)
            if not self.name:
                raise ValueError('Must provide a name for a DNS record within constructor OR separately.')

            for attr in ('_public_ips','_private_ips','_cnames'):
                value = set()
                for list in self.__dict__[attr]:
                    value.add(tuple(list))
                setattr(self, attr, value)
            for _,list in self.resources.items():
                list = set(list)
            self.subnets = set(self.subnets)

        elif re.fullmatch(dns_name_pattern, name):
            self.name = name.lower()
            if root: self.root = root.lower()
            self.location = None
            self.role = None

            # destinations
            self._public_ips = set()
            self._private_ips = set()
            self._cnames = set()
            self.resources = defaultdict(set)

            self.subnets = set()

        else:
            raise ValueError('Must provide a valid name for dns record (some FQDN) or a valid constructor dict.')

    # switch to case match on 2021-04-10
    def link(self, string: str, type: str, source: str=None):
        """
        Adds a link to the given object. Source is required for ip/ipv4 and domain link types.
        """
        if isinstance(string, str):
            string = string.lower().strip()
            if type in ('ipv4', 'ip', 'domain', 'cname'):
                if source:
                    if type in ('ipv4', 'ip'):
                        if iptools.valid_ip(string):
                            if iptools.public_ip(string):
                                self._public_ips.add((string, source))
                            else:
                                self._private_ips.add((string, source))
                        else:
                            raise ValueError(f'"{string}" is not a valid ipv4 address.')

                    elif type in ('domain', 'cname'):
                        if re.fullmatch(dns_name_pattern, string):
                            self._cnames.add((string, source))
                        else:
                            raise ValueError(f'Domain {string} is not valid.')
                else:
                    raise ValueError(f'Source is required for links of type {type}')
                
            else:
                self.resources[type].add(string)
            
            self.update()

        else:
            raise TypeError('DNS destination must be provided as string')

    @property
    def destinations(self) -> dict:
        return (self.resources | {
            'public_ips': self.public_ips,
            'private_ips': self.private_ips,
            'cnames': self.cnames,
        })

    @property
    def public_ips(self) -> list[str]:
        return [ip for ip,_ in self._public_ips]

    @property
    def private_ips(self) -> list[str]:
        return [ip for ip,_ in self._private_ips]

    @property
    def ips(self) -> list[str]:
        return self.public_ips + self.private_ips

    @property
    def _ips(self) -> set[Tuple[str, str]]:
        return self._public_ips.union(self._private_ips)

    @property
    def cnames(self) -> list[str]:
        return [cname for cname,_ in self._cnames]

    def update(self):
        for ip in self.private_ips:
            self.subnets.add(iptools.sort(ip))
        self.location = locate(self.ips)


class PTRRecord:
    """
    Reverse DNS record
    """
    ipv4: str
    name: str
    subnet: str
    root: str
    location: str
    unused: bool
    nat: str

    def __init__(self, ip: str, root: str=None, source: str=None, unused: bool=False):
        if iptools.valid_ip(ip):
            self.ipv4 = ip
            self.name = ip
            self.subnet = iptools.sort(ip)
            if root: self.root = root.lower()
            self.source = source
            self.unused = unused
            self.location = locate(self.ipv4)

            self._ptr = set()
            self.implied_ptr = set()
            self.nat = None
        else:
            raise ValueError('Must provide a valid name for ptr record (some IPv4)')

    def link(self, name, source):
        if re.fullmatch(dns_name_pattern, name):
            self._ptr.add((name, source))
    
    @property
    def ptr(self):
        return [ptr for ptr,_ in self._ptr]
    
    def discoverImpliedPTR(self, forward_dns: dict[str, DNSRecord]):
        for domain, dns in forward_dns.items():
            if self.name in dns.ips:
                self.implied_ptr.add(domain)


class JSONEncoder(json.JSONEncoder):
    """
    JSON Encoder compatible with DNSRecord and PTRRecord, sets, and datetime objects
    """
    def default(self, obj):
        """
        :meta private:
        """
        if isinstance(obj, DNSRecord) or isinstance(obj, PTRRecord):
            return obj.__dict__
        elif isinstance(obj, set):
            return sorted(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

###################################
# DNSRecord convenience functions #
###################################

def merge_sets(dns1: DNSRecord, dns2: DNSRecord) -> DNSRecord:
    """
    Simple merge of any sets of found in two dns objects
    """
    if isinstance(dns1, DNSRecord) and isinstance(dns2, DNSRecord):
        dns1_inf = dns1.__dict__
        dns2_inf = dns2.__dict__
        for attr in dns2_inf:
            if isinstance(dns2_inf[attr], set):
                dns1_inf[attr] = dns1_inf[attr].union(dns2_inf[attr])
        return dns1
    else:
        raise TypeError(f'Arguments must be dns objects, not {type(dns1)}, {type(dns2)}')

def integrate(superset: dict[str, DNSRecord], dns_set: dict[str, DNSRecord]) -> dict[str, DNSRecord]:
    """
    Integrates some set of dns records into a master set
    """
    for domain in dns_set:
        dns = dns_set[domain]
        if domain not in superset:
            superset[dns.name] = dns
        else:
            superset[domain] = merge_sets(superset[domain], dns_set[domain])

@handle
def loadDNS(file: Union[str, DirEntry]) -> dict[str, DNSRecord]:
    """
    Loads some json file as a set of DNSRecords
    """
    d = {}
    with open(file, 'r') as stream:
        jsondata = json.load(stream)
        for key, constructor in jsondata.items():
            d[key] = DNSRecord(key, constructor=constructor)
    return d

@critical
def writeDNS(dns_set: dict[str, DNSRecord], file: str):
    """
    Writes dns set to json file
    """
    with open(file, 'w') as dns:
        dns.write(json.dumps(dns_set, cls=JSONEncoder, indent=2))

#######################################
# Miscellaneous convenience functions #
#######################################

def xslt(xsl, src, out=None):
    """
    Runs some xslt using Saxon
    """
    xsltpath = 'java -jar /usr/local/bin/saxon-he-10.3.jar'
    if out:
        subprocess.run(f'{xsltpath} -xsl:{xsl} -s:{src} -o:{out}', shell=True)
    else:
        subprocess.run(f'{xsltpath} -xsl:{xsl} -s:{src}', shell=True)


@critical
def loadConfig():
    """
    Loads the DNS config as a global var if it exists
    """
    global config
    try:
        with open('src/config.json', 'r') as stream:
            config = json.load(stream)
    except FileNotFoundError:
        config = {'exclusions': []}


def fileFetchRecursive(dir: Union[str, DirEntry]) -> list[str]:
    """
    Returns a list of paths of all files descended from some directory.
    """
    if isinstance(dir, DirEntry):
        dir = dir.path
    elif not isinstance(dir, str):
        raise ValueError(f'Directory must be one of: str, os.DirEntry; Not {type(dir)}')
    
    fileset = []
    for file in scandir(dir):
        if file.is_dir():
            fileset += fileFetchRecursive(file)
        elif file.is_file():
            fileset.append(file.path)
    return fileset

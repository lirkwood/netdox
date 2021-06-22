"""
This module contains any multi-purpose or generic code for use by both internal processes and plugins.

This script is mostly to improve the development process and encourage code reuse. 
It contains the two main classes used within Netdox, *DNSRecord* and *PTRRecord*, which represent all the DNS records which share a name.
It also defines two decorators which are used throughout Netdox, and some other functions which became useful across multiple scripts.
"""

from __future__ import annotations
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
authdict = {}

def auth():
    global authdict
    """
    Returns the contents of the main configuration file, ``authentication.json``.
    If the file has not yet been opened in this instance, it is opened and read first.

    :Returns:
        A dictionary containing the authentication/configuration details for PageSeeder and any plugins which use it.
    """
    if not authdict:
        with open('src/authentication.json', 'r') as stream:
            authdict = json.load(stream)
    return authdict

dns_name_pattern = re.compile(r'([a-zA-Z0-9_-]+\.)+[a-zA-Z0-9_-]+')

##############
# Decorators #
##############

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


global location_map, location_pivot
location_map, location_pivot = {}, {}

def loadLocations():
    global location_map, location_pivot
    try:
        with open('src/locations.json', 'r') as stream:
            location_map = json.load(stream)
    except Exception:
        return None

    for location in location_map:
        for subnet in location_map[location]:
            location_pivot[subnet] = location

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
        for match in location_pivot:
            if iptools.subn_contains(match, subnet):
                mask = int(match.split('/')[-1])
                if mask not in matches:
                    matches[mask] = []
                matches[mask].append(location_pivot[match])

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

    def __init__(self, name: str=None, root: str=None):
        if re.fullmatch(dns_name_pattern, name):
            self.name = name.lower()
            if root: 
                self.root = root.lower()
            else:
                self.root = None
            self.location = None
            self.role = None

            # destinations
            self._public_ips = set()
            self._private_ips = set()
            self._cnames = set()
            self.resources = defaultdict(set)

            self.subnets = set()

        else:
            raise ValueError('Must provide a valid name for dns record (some FQDN)')

    @classmethod
    def from_dict(cls, object: dict):
        """
        Instantiates a DNSRecord from a dictionary.
        """
        record = cls(object['name'])
        for k, v in object.items():
            setattr(record, k, v)

        for attr in ('_public_ips','_private_ips','_cnames'):
            value = set()
            for list in record.__dict__[attr]:
                value.add(tuple(list))
            setattr(record, attr, value)

        for type, list in record.resources.items():
            record.resources[type] = set(list)

        record.subnets = set(record.subnets)
        record.update()
        
        return record

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
        """
        Property: returns a dictionary of all outgoing links from this record.
        """
        return (self.resources | {
            'public_ips': self.public_ips,
            'private_ips': self.private_ips,
            'cnames': self.cnames,
        })

    @property
    def _ips(self) -> set[Tuple[str, str]]:
        return self._public_ips.union(self._private_ips)

    @property
    def public_ips(self) -> list[str]:
        """
        Property: returns all IPs from this record that are outside of protected ranges.
        """
        return list(set([ip for ip,_ in self._public_ips]))

    @property
    def private_ips(self) -> list[str]:
        """
        Property: returns all IPs from this record that are inside a protected range.
        """
        return list(set([ip for ip,_ in self._private_ips]))

    @property
    def ips(self) -> list[str]:
        """
        Property: returns all IPs from this record.
        """
        return list(set(self.public_ips + self.private_ips))

    @property
    def cnames(self) -> list[str]:
        """
        Property: returns all CNAMEs from this record.
        """
        return list(set([cname for cname,_ in self._cnames]))

    def update(self):
        """
        Updates subnet and location data for this record.
        """
        for ip in self.private_ips:
            self.subnets.add(iptools.sort(ip))
        if location_map:
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
            if root: 
                self.root = root.lower()
            else:
                self.root = None
            self.source = source
            self.unused = unused
            self.location = locate(self.ipv4)

            self._ptr = set()
            self.implied_ptr = set()
            self.nat = None
        else:
            raise ValueError('Must provide a valid name for ptr record (some IPv4)')

    def link(self, name, source):
        """
        Adds a link to a domain.
        """
        if re.fullmatch(dns_name_pattern, name):
            self._ptr.add((name, source))
    
    @property
    def ptr(self):
        """
        Property: returns all domains from this record.
        """
        return [ptr for ptr,_ in self._ptr]
    
    def discoverImpliedPTR(self, forward_dns: DNSSet):
        for record in forward_dns:
            if self.name in record.ips:
                self.implied_ptr.add(record.name)


class DNSSet:
    """
    Container class for DNSRecords or PTRRecords
    """
    type: str
    _records: dict[str, Union[DNSRecord, PTRRecord]]

    def __init__(self, type: str = 'forward') -> None:
        if type not in ('forward', 'reverse'):
            raise ValueError(f'Unknown DNS set type {type}; Must be one of: forward, reverse')
        self.type = type
        self._records = {}

    def __repr__(self) -> str:
        return f'{self.type.capitalize()} DNS set'

    @property
    def records(self):
        """
        Property: returns a list of DNSRecord/PTRRecord objects in this set.
        """
        return list(self._records.values())

    @property
    def names(self):
        """
        Property: returns a list of all record names in this set.
        """
        return list(self._records.keys())

    def __getitem__(self, key: str) -> Union[DNSRecord, PTRRecord]:
        """
        Return a record given its name
        """
        return self._records[key]

    def __setitem__(self, key: str, val: Union[DNSRecord, PTRRecord]) -> None:
        """
        Overwrite a record given its name
        """
        self._records[key] = val

    def __delitem__(self, key: str) -> None:
        """
        Delete a record given its name
        """
        del self._records[key]

    def __contains__(self, key: str) -> bool:
        """
        Returns true if the set has a record with the given name
        """
        return self._records.__contains__(key)

    def __iter__(self) -> Union[DNSRecord, PTRRecord]:
        """
        Iterate over the records in the set
        """
        yield from self.records

    def add(self, record: Union[DNSRecord, PTRRecord]) -> None:
        """
        Add a record to the set, or merge with existing record if necessary
        """
        if self.type == 'forward' and not isinstance(record, DNSRecord):
            raise TypeError('Can only add DNSRecord to forward DNSSet')
        elif self.type == 'reverse' and not isinstance(record, PTRRecord):
            raise TypeError('Can only add PTRRecord to reverse DNSSet')

        name = record.name.lower()
        if name not in self._records:
            self._records[name] = record
        else:
            self._records[name] = merge_records(self._records[name], record)
    
    def to_json(self) -> str:
        """
        Serialises the set to a JSON string
        """
        return json.dumps({
            'type': self.type,
            'records': self.records
        }, indent = 2, cls = JSONEncoder)

    @classmethod
    def from_json(cls, constructor: str) -> DNSSet:
        """
        Deserialises a DNSSet from a JSON string
        """
        with json.loads(constructor) as spec:
            if spec['type'] == 'forward':
                recordClass = DNSRecord
            else:
                recordClass = PTRRecord

            new_set = cls(spec['type'])
            for record_dict in spec['records']:
                record = recordClass.from_dict(record_dict)
                new_set.add(record)
        return new_set


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
        else:
            return super().default(self, obj)

#######################################
# Miscellaneous convenience functions #
#######################################

def merge_records(dns1: Union[DNSRecord, PTRRecord], dns2: Union[DNSRecord, PTRRecord]) -> Union[DNSRecord, PTRRecord]:
    """
    Merge of two DNSRecords or two PTRRecords
    """
    if isinstance(dns1, (DNSRecord, PTRRecord)) and isinstance(dns2, (DNSRecord, PTRRecord)) and type(dns1) == type(dns2):
        if dns1.name == dns2.name:
            dns1_inf = dns1.__dict__
            dns2_inf = dns2.__dict__
            for attr, val in dns2_inf.items():
                if isinstance(val, set):
                    dns1_inf[attr] = dns1_inf[attr].union(dns2_inf[attr])

            if not dns1.root and dns2.root:
                dns1.root = dns2.root
            
            if isinstance(dns1, DNSRecord):
                for resource, links in dns2_inf['resources'].items():
                    dns1_inf['resources'][resource] = dns1_inf['resources'][resource].union(links)
                dns1.update()
            
            return dns1
        else:
            raise ValueError('Cannot merge records with different names')
    else:
        raise TypeError(f'Arguments be similar dns objects, not {type(dns1)}, {type(dns2)}')


def xslt(xsl: str, src: str, out: bool = None):
    """
    Runs some xslt using Saxon
    """
    xsltpath = 'java -jar /usr/local/bin/saxon-he-10.3.jar'
    if out:
        subprocess.run(f'{xsltpath} -xsl:{xsl} -s:{src} -o:{out}', shell=True)
    else:
        subprocess.run(f'{xsltpath} -xsl:{xsl} -s:{src}', shell=True)

global config
config = {'exclusions': []}

def loadConfig():
    """
    Loads the DNS config as a global var if it exists
    """
    global config
    try:
        with open('src/config.json', 'r') as stream:
            config = json.load(stream)
    except FileNotFoundError:
        pass


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

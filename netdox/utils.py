"""
This module contains any multi-purpose or generic code for use by both internal processes and plugins.

This script is mostly to improve the development process and encourage code reuse. 
It contains the two main classes used within Netdox, *DNSRecord* and *PTRRecord*, which represent all the DNS records which share a name.
It also defines two decorators which are used throughout Netdox, and some other functions which became useful across multiple scripts.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from functools import wraps
from os import DirEntry, scandir
from sys import argv
from traceback import format_exc
from typing import Iterable, Union

import iptools

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

#################
# Location Data #
#################

global location_map, location_pivot
try:
    with open('src/locations.json', 'r') as stream:
        location_map = json.load(stream)
except Exception:
    location_map = {}
location_pivot = {}

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
    else:
        raise TypeError(f'IP set must be one of: str, Iterable[str]; Not {type(ip_set)}')

    global location_map, location_pivot

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


# class DomainSet:
#     """
#     Container class for Domains
#     """

#     def __init__(self, domains: list[Domain]) -> None:
#         self.domains = domains

#     def __repr__(self) -> str:
#         return f'{self.type.capitalize()} DNS set'

#     @property
#     def records(self):
#         """
#         Property: returns a list of DNSRecord/PTRRecord objects in this set.
#         """
#         return list(self._records.values())

#     @property
#     def names(self):
#         """
#         Property: returns a list of all record names in this set.
#         """
#         return list(self._records.keys())

#     def __getitem__(self, key: str) -> Union[DNSRecord, PTRRecord]:
#         """
#         Return a record given its name
#         """
#         return self._records[key]

#     def __setitem__(self, key: str, val: Union[DNSRecord, PTRRecord]) -> None:
#         """
#         Overwrite a record given its name
#         """
#         self._records[key] = val

#     def __delitem__(self, key: str) -> None:
#         """
#         Delete a record given its name
#         """
#         del self._records[key]

#     def __contains__(self, key: str) -> bool:
#         """
#         Returns true if the set has a record with the given name
#         """
#         return self._records.__contains__(key)

#     def __iter__(self) -> Union[DNSRecord, PTRRecord]:
#         """
#         Iterate over the records in the set
#         """
#         yield from self.records

#     def add(self, record: Union[DNSRecord, PTRRecord]) -> None:
#         """
#         Add a record to the set, or merge with existing record if necessary
#         """
#         if self.type == 'forward' and not isinstance(record, DNSRecord):
#             raise TypeError('Can only add DNSRecord to forward DNSSet')
#         elif self.type == 'reverse' and not isinstance(record, PTRRecord):
#             raise TypeError('Can only add PTRRecord to reverse DNSSet')

#         name = record.name.lower()
#         if name not in self._records:
#             self._records[name] = record
#         else:
#             self._records[name] = merge_records(self._records[name], record)
    
#     def to_json(self) -> str:
#         """
#         Serialises the set to a JSON string
#         """
#         return json.dumps({
#             'type': self.type,
#             'records': self.records
#         }, indent = 2, cls = JSONEncoder)

#     @classmethod
#     def from_json(cls, constructor: str) -> DNSSet:
#         """
#         Deserialises a DNSSet from a JSON string
#         """
#         with json.loads(constructor) as spec:
#             if spec['type'] == 'forward':
#                 recordClass = DNSRecord
#             else:
#                 recordClass = PTRRecord

#             new_set = cls(spec['type'])
#             for record_dict in spec['records']:
#                 record = recordClass.from_dict(record_dict)
#                 new_set.add(record)
#         return new_set


from network import NetworkObject
class JSONEncoder(json.JSONEncoder):
    """
    JSON Encoder compatible with DNSRecord and PTRRecord, sets, and datetime objects
    """
    def default(self, obj):
        """
        :meta private:
        """
        if issubclass(obj, NetworkObject):
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

# def merge_records(dns1: Union[DNSRecord, PTRRecord], dns2: Union[DNSRecord, PTRRecord]) -> Union[DNSRecord, PTRRecord]:
#     """
#     Merge of two DNSRecords or two PTRRecords
#     """
#     if isinstance(dns1, (DNSRecord, PTRRecord)) and isinstance(dns2, (DNSRecord, PTRRecord)) and type(dns1) == type(dns2):
#         if dns1.name == dns2.name:
#             dns1_inf = dns1.__dict__
#             dns2_inf = dns2.__dict__
#             for attr, val in dns2_inf.items():
#                 if isinstance(val, set):
#                     dns1_inf[attr] = dns1_inf[attr].union(dns2_inf[attr])

#             if not dns1.root and dns2.root:
#                 dns1.root = dns2.root
            
#             if isinstance(dns1, DNSRecord):
#                 dns1.update()
            
#             return dns1
#         else:
#             raise ValueError('Cannot merge records with different names')
#     else:
#         raise TypeError(f'Arguments be similar dns objects, not {type(dns1)}, {type(dns2)}')


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

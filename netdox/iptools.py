"""
Module of useful classes and functions for manipulating IPv4 addresses and subnets.
"""

import re
from typing import Any, Generator, Union

###############
# Class: ipv4 #
###############

class ipv4:
    def __init__(self, ip):
        self.raw = ip
        self.valid = valid_ip(self.raw)
        if self.valid:
            self.ipv4 = self.raw
            self.int = cidr2int(self.ipv4)
            self.subnet = sort(self.ipv4)
            self.public = public_ip(self.ipv4)
            self.octets = self._octets()
        else:
            raise ValueError('Cannot instantiate an ipv4 using an invalid address')

    def in_subnet(self, subnet, verbose=False):
        return subn_contains(subnet, self.ipv4, verbose)  

    def _octets(self):
        a = []
        for o in self.ipv4.split('.'):
            a.append(o)
        return a

#################
# Class: subnet #
#################

class subnet:
    def __init__(self, raw):
        self.raw = raw
        self.valid = valid_subnet(self.raw)
        if self.valid:
            self.min_addr = subn_floor(self.raw)
            self._mask = int(self.raw.split('/')[-1])

            self.subnet = self.min_addr +'/'+ str(self._mask)

            self.octets = self.subnet.split('/')[0].split('.')
            for octet in range(4):
                self.octets[octet] = int(self.octets[octet])
        else:
            raise ValueError(f'Invalid subnet: {raw}')
    
    # returns value of subnet mask (int)
    @property
    def mask(self):
        return self._mask
    
    # sets new value for subnet mask and reinitialises class instance (accepts int or str, with or without leading '/')
    @mask.setter
    def mask(self, new_mask):
        str_new_mask = str(new_mask)
        if re.match(r'/*[0-9]{1,2}', str_new_mask):
            self._mask = int(str_new_mask.strip('/'))
            self.__init__(self.min_addr +'/'+ str(self._mask))
        else:
            raise ValueError('Invalid subnet mask provided. Must be in between 0 and 31 inclusive.')


    def equiv(self, mask):
        return subn_equiv(self.subnet, self.mask, mask)
    
    def iterate(self):
        return subn_iter(self)

####################
# Module functions #
####################

## Useful regex patterns

regex_ip = re.compile(r'((1?[0-9]{0,2}|2[0-4][0-9]|25[0-5])\.){3}(1?[0-9]{0,2}|2[0-4][0-9]|25[0-5])')
regex_subnet = re.compile(r'((1?[0-9]{0,2}|2[0-4][0-9]|25[0-5])\.){3}(1?[0-9]{0,2}|2[0-4][0-9]|25[0-5])/([0-2]?[0-9]|3[0-1])')


## Validation

def valid_ip(string: str) -> bool:
    """
    Tests if a string is valid as a CIDR IPv4 address
    """
    if re.fullmatch(regex_ip, string):
        for octet in string.split('.'):
            if int(octet) >= 0 and int(octet) <= 255:
                pass
            else:
                return False
            return True
    else:
        return False
    
def valid_subnet(string: str) -> bool:
    """
    Tests if a string is valid as a CIDR IPv4 subnet
    """
    if re.fullmatch(regex_subnet, string):
        return True
    else:
        return False

def public_ip(string: str) -> bool:
    """
    Tests if an IP address is part of the public or private namespace
    """
    if subn_contains('192.168.0.0/16', string):
        return False
    elif subn_contains('10.0.0.0/8', string):
        return False
    elif subn_contains('172.16.0.0/12', string):
        return False
    else:
        return True


## Subnet functions

def subn_floor(subn: Union[str, subnet]) -> str:
    """
    Returns the lowest IP address in a subnet
    """
    if isinstance(subn, subnet):
        subn = subn.subnet
    elif not isinstance(subn, str):
        raise TypeError(f'Subnet object must be one of: str, subnet; Not {type(subn)}')
    elif not valid_subnet(subn):
        raise ValueError(f'Invalid subnet {subn}')

    mask = int(subn.split('/')[-1])
    addr = subn.split('/')[0]
    octets = addr.split('.')
    for octet in range(4):
        octets[octet] = int(octets[octet])

    split_octet = mask // 8
    
    octet_mask = mask % 8
    if octet_mask:
        octets[split_octet] >>= 8 - octet_mask
        octets[split_octet] <<= 8 - octet_mask  # discard all bits after mask
    else:
        octets[split_octet] = 0

    str_octets = []
    for octet in range(4):
        if octet > split_octet:
            octets[octet] = 0
        str_octets.append(str(octets[octet]))
            
    min_addr = '.'.join(str_octets)
    return min_addr

def subn_bounds(subn: Union[str, subnet], binary: bool = False) -> dict[str, int]:
    """
    Returns a dictionary of the bounds of a subnet, as integers
    """
    if isinstance(subn, subnet):
        subn = subn.subnet
    elif not isinstance(subn, str):
        raise TypeError(f'Subnet object must be one of: str, subnet; Not {type(subn)}')

    lower = cidr2int(subn_floor(subn))
    bounds = {'lower': lower}

    mask = int(subn.split('/')[-1])

    upper = lower
    for bit in range(32 - mask):
        upper += 2**bit    #set all bits out of mask range
    bounds['upper'] = upper

    if not binary:
        for bound in bounds:
            bounds[bound] = int2cidr(bounds[bound])

    return bounds
    
def subn_equiv(subn: Union[str, subnet], new_mask: int) -> list[str]:
    """
    Converts a subnet to new subnet(s) with the given mask.
    """
    if isinstance(subn, subnet):
        old_mask = subn.mask
    elif isinstance(subn, str):
        if valid_subnet(subn):
            old_mask = int(subn.split('/')[-1])
        else:
            raise ValueError('Cannot find equivalent subnets to invalid subnet.')
    else:
        raise TypeError(f'Subnet object must be one of: str, subnet; Not {type(subn)}')

    subnets = []
    int_min_addr = cidr2int(subn_floor(subn))

    if new_mask > old_mask:
        for _ in range(2**(new_mask - old_mask)):
            min_addr = int2cidr(int_min_addr)
            new_subnet = min_addr +'/'+ str(new_mask)
            subnets.append(new_subnet)

            int_min_addr += (2**(32-new_mask))
    else:
        new_subnet = subn_floor(subn) +'/'+ str(new_mask)
        subnets.append(subn_floor(new_subnet) +'/'+ str(new_mask))

    return subnets

def subn_contains(subn: Union[str, subnet], object: Union[str, ipv4, subnet], verbose: bool = False) -> bool:
    """
    Tests if a subnet contains an IP or subnet
    """
    if isinstance(subn, subnet):
        subn = subn.subnet
    elif not isinstance(subn, str):
        raise TypeError(f'Subnet object must be one of: str, subnet; Not {type(subn)}')

    # Validate input object
    if isinstance(object, ipv4):
        ip = object.ipv4
    elif isinstance(object, subnet):
        bounds = subn_bounds(object)
        return (subn_contains(subn, bounds['upper']) & subn_contains(subn, bounds['lower']))
    elif isinstance(object, str):
        if valid_ip(object):
            ip = object
        elif valid_subnet(object):
            bounds = subn_bounds(object)
            return (subn_contains(subn, bounds['upper']) & subn_contains(subn, bounds['lower']))
        else:
            raise ValueError(f'Object to be tested must be a valid ipv4 or subnet.')
    else:
        raise TypeError(f'IP object must be one of: str, ipv4; Not {type(object)}')

    bin_ip = cidr2int(ip)
    bounds = subn_bounds(subn, binary=True)
    if bin_ip >= int(bounds['lower']) and bin_ip <= int(bounds['upper']):
        if verbose:
            print(f'[INFO][iptools] IP Address {ip} is within subnet {subn}.')
        return True
    else:
        if verbose:
            print(f'[INFO][iptools] IP Address {ip} is outside subnet {subn}.')
        return False
    
def subn_iter(subn: Union[str, subnet]) -> Generator[str, Any, Any]:
    """
    Returns a generator which yields each IP address in a subnet, lowest first
    """
    if isinstance(subn, subnet):
        subn = subn.subnet
    elif not isinstance(subn, str):
        raise TypeError(f'Subnet object must be one of: str, subnet; Not {type(subn)}')
        
    bounds = subn_bounds(subn, binary=True)
    for ip in range((bounds['upper'] - bounds['lower'])+ 1):    #+1 to include upper bound as bounds are inclusive
        yield int2cidr(ip+bounds['lower'])


## Conversion functions

def cidr2int(ipv4: str) -> int:
    """
    Converts an IPv4 address given in CIDR from to an integer
    """
    octets = ipv4.split('.')
    int_ip = 0
    for octet in range(4):
        int_ip += int(octets[octet]) << (8 * (3 - octet))
    return int_ip

def int2cidr(ipv4: int) -> str:
    """
    Converts an IPv4 address to a string in CIDR form
    """
    bin_str = bin(ipv4)[2:].zfill(32)
    str_octets = [str(int(bin_str[octet:octet+8], base = 2)) for octet in range(0,32,8)]
    return '.'.join(str_octets)


## Other

def search_string(string: str, object: str = 'ipv4', delimiter: str = None) -> list[str]:
    """
    Searches a string for all instances of an object: either an IPv4 address (ipv4) or an IPv4 subnet (ipv4_subnet).
    Searches in chunks delimited by the provided value (default = newline).
    """
    if object == 'ipv4':
        validate = valid_ip
        pattern = regex_ip
    elif object == 'ipv4_subnet':
        validate = valid_subnet
        pattern = regex_subnet
    else:
        raise TypeError(f'Search object must be one of: ipv4, ipv4_subnet; Not {object}')

    outlist = []
    for line in string.split(delimiter):
        # Ignore comments
        if not (line.startswith('#') or line.startswith('//')):
            cleanline = line.strip()
            if validate(cleanline):
                outlist.append(cleanline)
            else:
                for match in re.finditer(pattern, cleanline):
                    outlist.append(match[0])
    outlist = list(dict.fromkeys(outlist))
    return outlist


def sort(ip: Union[str, ipv4], mask: int = 24) -> str:
    """
    Returns the subnet with a given mask an IPv4 address is in
    """
    if isinstance(ip, ipv4):
        ip = ip.ipv4
    elif not isinstance(ip, str):
        raise TypeError(f'IPv4 object must be one of: ipv4, str; Not {type(ip)}')

    if isinstance(mask, int):
        mask = str(mask)
    elif not isinstance(mask, str):
        raise TypeError(f'Subnet mask must be one of: int, str; Not {type(mask)}')

    subn = ip +'/'+ str(mask)
    return f'{subn_floor(subn)}/{str(mask)}'
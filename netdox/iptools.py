"""
Module of useful classes and functions for manipulating IPv4 addresses and subnets.

Not a part of Netdox.
"""

import re
from types import prepare_class
from typing import Union

###############
# Class: ipv4 #
###############

class ipv4:
    def __init__(self, ip):
        self.raw = ip
        self.valid = valid_ip(self.raw)
        if self.valid:
            self.ipv4 = self.raw
            self.binary = cidr2binary(self.ipv4)
            self.subnet = sort(self.ipv4)
            self.public = public_ip(self.ipv4)
            self.octets = self._octets()
        else:
            self.ipv4 = None
            self.binary = None
            self.subnet = None
            self.octets = None

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

regex_ip = re.compile(r'([0-9]{1,3}\.){3}[0-9]{1,3}')
regex_subnet = re.compile(r'([0-9]{1,3}\.){3}[0-9]{1,3}/([0-2]?[0-9]|3[0-1])')


## Validation

# returns boolean if given str is valid within CIDR ipv4 format
def valid_ip(string):
    if re.fullmatch(regex_ip, string):
        for octet in string.split('.'):
            if int(octet) >= 0 and int(octet) <= 255:
                pass
            else:
                return False
            return True
    else:
        return False
    
def valid_subnet(string):
    if re.fullmatch(regex_subnet, string):
        return True
    else:
        return False

def public_ip(string):
    if subn_contains('192.168.0.0/16', string):
        return False
    elif subn_contains('10.0.0.0/8', string):
        return False
    elif subn_contains('172.16.0.0/12', string):
        return False
    else:
        return True

## Subnet functions

# returns lowest ip address in subnet (CIDR ipv4)
def subn_floor(subn):
    if isinstance(subn, subnet):
        subn = subn.subnet
    elif not isinstance(subn, str):
        raise TypeError(f'Subnet object must be one of: str, subnet; Not "{type(subn)}"')

    if re.fullmatch(r'([0-9]{1,3}\.){3}[0-9]{1,3}/([0-2]?[0-9]|3[0-1])', subn):
        mask = int(subn.split('/')[-1])
        addr = subn.split('/')[0]
        octets = addr.split('.')
        for octet in range(4):
            octets[octet] = int(octets[octet])

        split_octet = mask // 8
        bit_mask = mask % 8

        new_octet = 0
        for bit in range(bit_mask):
            new_octet += 2**(8 - bit)
        octets[split_octet] = new_octet

        str_octets = []
        for octet in range(4):
            if octet > split_octet:
                octets[octet] = 0
            str_octets.append(str(octets[octet]))
                
        min_addr = '.'.join(str_octets)
        return min_addr

    else:
        raise ValueError('Please provide a valid address (0.0.0.0 -> 255.255.255.255) and subnet mask (address/0 -> address/31)')

# Returns dict with lowest (key=lower) and highest (key=upper) ip addresses in subnet (32-bit wide binary strs)
def subn_bounds(subn, binary=False):
    if isinstance(subn, subnet):
        subn = subn.subnet
    elif not isinstance(subn, str):
        raise TypeError(f'Subnet object must be one of: "str", "subnet"; Not "{type(subn)}"')

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
# returns list obj containing some subnets with a given mask (CIDR ipv4 format).
# The union of these has an equivalent namespace to the original subnet.
def subn_equiv(subn, new_mask):
    if isinstance(subn, subnet):
        if subn.valid:
            old_mask = subn.mask
        else:
            raise ValueError('Cannot find equivalent subnets to invalid subnet.')
    elif isinstance(subn, str):
        if valid_subnet(subn):
            old_mask = int(subn.split('/')[-1])
        else:
            raise ValueError('Cannot find equivalent subnets to invalid subnet.')
    else:
        raise TypeError(f'Subnet object must be one of: "str", "subnet"; Not "{type(subn)}"')

    if isinstance(new_mask, str):
        new_mask = int(new_mask.strip('/'))
    subnets = []
    bin_min_addr = cidr2binary(subn_floor(subn))

    if new_mask > old_mask:
        int_min_addr = int(bin_min_addr, 2)

        for i in range(2**(new_mask - old_mask)):
            min_addr = int2cidr(int_min_addr)
            new_subnet = min_addr +'/'+ str(new_mask)
            subnets.append(new_subnet)

            int_min_addr += (2**(32-new_mask))
    else:
        new_subnet = subn_floor(subn) +'/'+ str(new_mask)
        subnets.append(subn_floor(new_subnet) +'/'+ str(new_mask))

    return subnets

# returns boolean if ip (CIDR ipv4) is in given subnet
def subn_contains(subn: Union[str, subnet], object: Union[str, ipv4, subnet], verbose=False):
    # Validate subnet
    if isinstance(subn, subnet):
        subn = subn.subnet
    elif not isinstance(subn, str):
        raise TypeError(f'Subnet object must be one of: "str", "subnet"; Not "{type(subn)}"')

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
        raise TypeError(f'IP object must be one of: "str", "ipv4"; Not "{type(object)}"')

    bin_ip = int(cidr2binary(ip), base=2)
    bounds = subn_bounds(subn, binary=True)
    if bin_ip >= int(bounds['lower']) and bin_ip <= int(bounds['upper']):
        if verbose:
            print(f'[INFO][iptools] IP Address {ip} is within subnet {subn}.')
        return True
    else:
        if verbose:
            print(f'[INFO][iptools] IP Address {ip} is outside subnet {subn}.')
        return False
    
def subn_iter(subn):
    if isinstance(subn, subnet):
        subn = subn.subnet
    elif not isinstance(subn, str):
        raise TypeError(f'Subnet object must be one of: "str", "subnet"; Not "{type(subn)}"')
        
    bounds = subn_bounds(subn, binary=True)
    upper = int(bounds['upper'], 2)
    lower = int(bounds['lower'], 2)
    for ip in range((upper - lower)+ 1):    #+1 to include upper bound as bounds are inclusive
        yield int2cidr(ip+lower)

## Conversion functions

# converts ipv4 in CIDR format to 32 bit wide binary str
def cidr2binary(ipv4):
    bin_ip = ''
    for octet in ipv4.split('.'):
        bin_ip += bin(int(octet))[2:].zfill(8) 
    #strip 0b prefix and pad to size with 0s
    return bin_ip

# converts 32-bit unsigned binary str from given ipv4 using CIDR notation
def binary2cidr(bin_ip):
    cache = ''
    octets = []
    for index in range(32):
        cache += bin_ip[index]
        if (index+1) %8 == 0:
            octets.append(str(int(cache,2)))
            cache = ''
    return '.'.join(octets)

# converts integer to binary string (default width 32 bits)
def int2binary(integer, width=32):
    return bin(integer).replace('0b','').zfill(width)

def int2cidr(integer):
    return binary2cidr(int2binary(integer))

def cidr2int(ipv4):
    return int(cidr2binary(ipv4), 2)

## Other

def search_string(string, object, delimiter=None):
    if object == 'ipv4':
        validate = valid_ip
        pattern = regex_ip
    elif object == 'ipv4_subnet':
        validate = valid_subnet
        pattern = regex_subnet
    else:
        raise TypeError(f'Search object must be one of: ipv4, subnet; Not "{type(object)}".')

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


def sort(ip, mask=24):
    if isinstance(ip, ipv4):
        ip = ip.ipv4
    elif not isinstance(ip, str):
        raise TypeError('IPv4 object must be one of: ipv4, str ')

    if isinstance(mask, int):
        mask = str(mask)
    elif not isinstance(mask, str):
        raise TypeError('Subnet mask must be one of: int, str ')

    subn = ip +'/'+ str(mask)
    return f'{subn_floor(subn)}/{str(mask)}'
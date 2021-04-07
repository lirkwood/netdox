import re, math
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
            self.subnet = self.sort()
            self.public = self.is_public()
            self.octets = self._octets()
        else:
            self.ipv4 = None
            self.binary = None
            self.subnet = None
            self.octets = None

    # Used mainly within netdox to sort ips into predefined subnets
    def sort(self):
        bin_ip = int(self.binary, 2)
        sorted = False
        try:
            subndict = fetch_prefixes()
        except FileNotFoundError:
            # print('[WARNING][iptools.py] prefixes.txt not found. Sorting using default 255.255.255.0 subnet mask.')
            subndict = {}
        for prefix in subndict:
            if bin_ip >= int(subndict[prefix]['lower'], 2) and bin_ip <= int(subndict[prefix]['upper'], 2):
                sorted = True
                return prefix
        
        if not sorted:
            return '.'.join(self.ipv4.split('.')[:3]) + '.0/24'

    def in_subnet(self, subnet, verbose=False):
        return subn_contains(subnet, self.ipv4, verbose)  

    def is_public(self):
        if subn_contains('192.168.0.0/16', self.ipv4):
            return False
        elif subn_contains('10.0.0.0/8', self.ipv4):
            return False
        elif subn_contains('172.16.0.0/12', self.ipv4):
            return False
        else:
            return True

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
            self.subnet = None
            self._mask = None
            self.min_addr = None
            self.octets = []
    
    # returns value of subnet mask (int)
    @property
    def mask(self):
        return self._mask
    
    # sets new value for subnet mask and reinitialises class instance (accepts int or str, with or without leading '/')
    @mask.setter
    def mask(self, new_mask):
        if self.valid:
            str_new_mask = str(new_mask)
            if re.match(r'/*[0-9]{1,2}', str_new_mask):
                self._mask = int(str_new_mask.strip('/'))
                self.__init__(self.min_addr +'/'+ str(self._mask))
            else:
                print('[ERROR][iptools.py] Invalid subnet mask provided. Must be in between 0 and 31 inclusive.')
        else:
            print('[ERROR][iptools.py] Cannot set new subnet mask for invalid subnet.')


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
def subn_floor(subnet):
    if re.fullmatch(r'([0-9]{1,3}\.){3}[0-9]{1,3}/([0-2]?[0-9]|3[0-1])', subnet):
        mask = int(subnet.split('/')[-1])
        addr = subnet.split('/')[0]
        octets = addr.split('.')
        for octet in range(4):
            octets[octet] = int(octets[octet])

        split_octet = mask // 8
        bin_octet = bin(octets[split_octet])[2:].zfill(8)
        bit_mask = mask % 8

        new_octet = ''
        for bit in range(bit_mask):
            new_octet += bin_octet[bit]
        octets[split_octet] = int(new_octet.ljust(8,'0'), 2)

        str_octets = []
        for octet in range(4):
            if octet > split_octet:
                octets[octet] = 0
            str_octets.append(str(octets[octet]))
                
        min_addr = '.'.join(str_octets)
        return min_addr

    else:
        print('[ERROR][iptools.py] Please provide a valid address (0.0.0.0 -> 255.255.255.255) and subnet mask (address/0 -> address/31)')
        return None

# Returns dict with lowest (key=lower) and highest (key=upper) ip addresses in subnet (32-bit wide binary strs)
def subn_bounds(subn):
    if isinstance(subn, subnet):
        subn = subn.subnet
    elif not isinstance(subn, str):
        raise TypeError(f'Subnet object must be one of: "str", "subnet".; Not "{type(subn)}"')

    bounds = {}
    lower = cidr2binary(subn_floor(subn))
    bounds['lower'] = lower

    mask = int(subn.split('/')[-1])

    upper = str(lower)
    upper = upper[:mask]
    for i in range(32 - mask):
        upper += '1'    #set all bits out of mask range
    bounds['upper'] = upper

    return bounds

# returns list obj containing some subnets with a given mask (CIDR ipv4 format). The union of these is equivalent to
# the namespace of the original subnet
def subn_equiv(subn, new_mask):
    if isinstance(subn, subnet):
        if subn.valid:
            old_mask = subn.mask
        else:
            print('[ERROR][iptools.py] Cannot find equivalent subnets to invalid subnet.')
    elif isinstance(subn, str):
        if valid_subnet(subn):
            old_mask = int(subn.split('/')[-1])
        else:
            print('[ERROR][iptools.py] Cannot find equivalent subnets to invalid subnet.')
    else:
        print(f'[ERROR][iptools.py] Please provide a valid object; Must be one of: subnet, str; Not "{type(subn)}"')
        return None

    if isinstance(new_mask, str):
        new_mask = int(new_mask.strip('/'))
    subnets = []
    bin_min_addr = cidr2binary(subn_floor(subn))

    if new_mask > old_mask:
        int_min_addr = int(bin_min_addr, 2)

        for i in range(2**(new_mask - old_mask)):
            min_addr = binary2cidr(int2binary(int_min_addr))
            new_subnet = min_addr +'/'+ str(new_mask)
            subnets.append(new_subnet)

            int_min_addr += (2**(32-new_mask))
    else:
        new_subnet = subn_floor(subn) +'/'+ str(new_mask)
        subnets.append(subn_floor(new_subnet) +'/'+ str(new_mask))

    return subnets

# returns boolean if ip (CIDR ipv4) is in given subnet
def subn_contains(subn: Union[str, subnet], ip: Union[str, ipv4], verbose=False):
    # Validating input types
    if isinstance(subn, subnet):
        subn = subn.subnet
    elif not isinstance(subn, str):
        raise TypeError(f'[ERROR][iptools.py] Subnet object must be one of: "str", "subnet".; Not "{type(subn)}"')

    if isinstance(ip, ipv4):
        ip = ip.ipv4
    elif not isinstance(ip, str):
        raise TypeError(f'[ERROR][iptools.py] IP object must be one of: "str", "ipv4".; Not "{type(ip)}"')

    bin_ip = int(cidr2binary(ip), base=2)
    bounds = subn_bounds(subn)
    if bin_ip >= int(bounds['lower'],2) and bin_ip <= int(bounds['upper'],2):
        if verbose:
            print(f'[INFO][iptools.py] IP Address {ip} is within subnet {subn}.')
        return True
    else:
        if verbose:
            print(f'[INFO][iptools.py] IP Address {ip} is outside subnet {subn}.')
        return False
    
def subn_iter(subn):
    if isinstance(subn, subnet):
        print(subn.subnet)
        subn = subn.subnet
    elif not isinstance(subn, str):
        raise TypeError(f'[ERROR][iptools.py] Subnet object must be one of: "str", "subnet"; Not "{type(subn)}"')
    print(subn)
    print(type(subn))
        
    bounds = subn_bounds(subn)
    upper = int(bounds['upper'], 2)
    lower = int(bounds['lower'], 2)
    for ip in range((upper - lower)+ 1):    #+1 to include upper bound as bounds are inclusive
        yield binary2cidr(int2binary(ip+lower))

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
            raise TypeError(f'[ERROR][iptools.py] Search object must be one of: ipv4, subnet; Not "{type(object)}".')
            

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


# returns pre-defined subnets to use for sorting
def fetch_prefixes():
    prefixes = {}
    with open('src/prefixes.txt') as stream:
        for line in stream.read().splitlines():
            if line not in prefixes:
                prefixes[line] = subn_bounds(line)
    return prefixes


def sort(ip):
    if isinstance(ip, ipv4):
        ip = ip.ipv4
    elif not isinstance(ip, str):
        raise TypeError('[ERROR][iptools.py] IPv4 object must be one of: ipv4, str ')
    else:
        bin_ip = int(cidr2binary(ip), 2)
        sorted = False
        try:
            subndict = fetch_prefixes()
        except FileNotFoundError:
            # print('[WARNING][iptools.py] prefixes.txt not found. Sorting using default 255.255.255.0 subnet mask.')
            subndict = {}
        for prefix in subndict:
            if bin_ip >= int(subndict[prefix]['lower'], 2) and bin_ip <= int(subndict[prefix]['upper'], 2):
                sorted = True
                return prefix
        
        if not sorted:
            return '.'.join(ip.split('.')[:3]) + '.0/24'
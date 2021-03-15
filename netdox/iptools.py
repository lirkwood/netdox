import re, math
from types import prepare_class

class ipv4:
    def __init__(self, ip):
        self.raw = ip
        self.ipv4 = ip
        self.valid = self.valid_ip()
        if self.valid:
            self.binary = self.to_binary()
            self.subnet = self.sort()
            self.public = self.is_public()
            self.octets = self._octets()
        else:
            self.ipv4 = None
            self.binary = None
            self.subnet = None
            self.octets = None


    def to_binary(self):
        bin_ip = ''
        for octet in self.ipv4.split('.'):
            bin_ip += bin(int(octet))[2:].zfill(8) 
        #strip 0b prefix and pad to size with 0s
        return bin_ip

    def valid_ip(self):
        rawip = bytes(self.ipv4, 'utf-8')
        if re.match(r'([0-9]{1,3}\.){3}[0-9]{1,3}', self.ipv4):

            for char in re.findall(r'[^0-9.]',self.ipv4):
                print(f'[ERROR][iptools.py] Bad character {char} in ip: {rawip}')
                return False

            for octet in self.ipv4.split('.'):
                if len(octet) > 3 or len(octet) < 1:
                    print(f'[ERROR][iptools.py] Bad octet in ip: {rawip}')
                    return False
                elif int(octet) > 255 or int(octet) < 0:
                    print(f'[ERROR][iptools.py] Bad octet in ip: {rawip}')
                    return False

            if self.ipv4.count('.') != 3:
                print(f'[ERROR][iptools.py] Wrong number of octets in ip: {rawip}')
                return False

        else:
            return False
        return True

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
        bin_ip = int(self.binary, base=2)
        bounds = subn_bounds(subnet)
        if bin_ip >= int(bounds['lower'],2) and bin_ip <= int(bounds['upper'],2):
            if verbose:
                print(f'[INFO][iptools.py] IP Address {self.ipv4} is within subnet {subnet}')
            return True
        else:
            if verbose:
                print(f'[INFO][iptools.py] IP Address {self.ipv4} is outside subnet {subnet}')
            return False    

    def is_public(self):
        if in_subnet(self.ipv4, '192.168.0.0/16'):
            return False
        elif in_subnet(self.ipv4, '10.0.0.0/8'):
            return False
        elif in_subnet(self.ipv4, '172.16.0.0/12'):
            return False
        else:
            return True
    
    def iter_subnet(self):
        bounds = subn_bounds(self.subnet)
        upper = int(bounds['upper'], 2)
        lower = int(bounds['lower'], 2)
        for ip in range((upper - lower)+ 1):    #+1 to include upper bound as bounds are inclusive
            yield binary2cidr(int2bin(ip+lower))

    def _octets(self):
        a = []
        for o in self.ipv4.split('.'):
            a.append(o)
        return a

class subnet:
    def __init__(self, raw):
        self.raw = raw
        self.valid = self.valid_subnet()
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

    # returns boolean if subnet matches CIDR ipv4 format
    def valid_subnet(self):
        if re.fullmatch(r'([0-9]{1,3}\.){3}[0-9]{1,3}/([0-2]?[0-9]|3[0-1])', self.raw):
            return True
        else:
            return False
    
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


    # returns list obj containing some subnets with a given mask (CIDR ipv4 format). The union of these is equivalent to
    # the namespace of self.subnet
    def equiv(self, mask):
        if self.valid:
            if isinstance(mask, str):
                mask = int(mask.strip('/'))
            subnets = []
            bin_min_addr = cidr2binary(self.min_addr)

            if mask > self._mask:
                int_min_addr = int(bin_min_addr, 2)

                for i in range(2**(mask - self._mask)):
                    min_addr = binary2cidr(int2bin(int_min_addr))
                    subnet = min_addr +'/'+ str(mask)
                    subnets.append(subnet)

                    int_min_addr += (2**(32-mask))
            else:
                new_subnet = self.min_addr +'/'+ str(mask)
                subnets.append(subn_floor(new_subnet) +'/'+ str(mask))

                
            return subnets
        else:
            print('[ERROR][iptools.py] Cannot find equivalent subnets to invalid subnet.')

        

# __ User functions __

# returns boolean if given str is valid within CIDR ipv4 format
def valid_ip(ip, verbose=False):
    rawip = bytes(ip, 'utf-8')
    for octet in ip.split('.'):
        if len(octet) > 3 or len(octet) < 1: 
            if verbose:
                print(f'[ERROR][iptools.py] Bad octet in ip: {rawip}')
            return False
        elif int(octet) > 255 or int(octet) < 0:
            if verbose:
                print(f'[ERROR][iptools.py] Bad octet in ip: {rawip}')
            return False

    if ip.count('.') != 3:
        if verbose:
            print(f'[ERROR][iptools.py] Wrong number of octets in ip: {rawip}')
        return False

    for char in re.findall(r'[^0-9.]',ip):
        if verbose:
            print(f'[ERROR][iptools.py] Bad character {char} in ip: {rawip}')
        return False

    return True

# returns true if provided ip is not in one of the 3 predefined private subnets
def is_public(ip):
    if in_subnet(ip, '192.168.0.0/16'):
        return False
    elif in_subnet(ip, '10.0.0.0/8'):
        return False
    elif in_subnet(ip, '172.16.0.0/12'):
        return False
    else:
        return True

# converts ipv4 in CIDR format to 32 bit wide binary str
def cidr2binary(ip):
    bin_ip = ''
    for octet in ip.split('.'):
        bin_ip += bin(int(octet))[2:].zfill(8) 
    #strip 0b prefix and pad to size with 0s
    return bin_ip

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
def subn_bounds(string):
    bounds = {}
    lower = cidr2binary(subn_floor(string))
    bounds['lower'] = lower

    mask = int(string.split('/')[-1])

    upper = str(lower)
    upper = upper[:mask]
    for i in range(32 - mask):
        upper += '1'    #set all bits out of mask range
    bounds['upper'] = upper

    return bounds

# returns pre-defined subnets to use for sorting
def fetch_prefixes():
    prefixes = {}
    with open('src/prefixes.txt') as stream:
        for line in stream.read().splitlines():
            if line not in prefixes:
                prefixes[line] = subn_bounds(line)
    return prefixes

# returns boolean if ip (CIDR ipv4) is in given subnet
def in_subnet(ip, subnet, verbose=False):
    bin_ip = int(cidr2binary(ip), base=2)
    bounds = subn_bounds(subnet)
    if bin_ip >= int(bounds['lower'],2) and bin_ip <= int(bounds['upper'],2):
        if verbose:
            print('[INFO][iptools.py] IP Address {0} is within subnet {1}.'.format(ip, subnet))
        return True
    else:
        if verbose:
            print('[INFO][iptools.py] IP Address {0} is outside subnet {1}.'.format(ip, subnet))
        return False

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
def int2bin(i, width=32):
    return bin(i).replace('0b','').zfill(width)
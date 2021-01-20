import re

class parsed_ip:
    def __init__(self, ip):
        self.valid = self.valid_ip(ip)
        if self.valid:
            self.ipv4 = ip
            self.binary = self.binary_ip(ip)
            self.subnet = self.sort(ip, self.binary)


    def binary_ip(self, ip):
        bin_ip = ''
        for octet in ip.split('.'):
            bin_ip += bin(int(octet))[2:].zfill(8) 
        #strip 0b prefix and pad to size with 0s
        return bin_ip

    def valid_ip(self, ip):                                             #Requirements for validity:
        rawip = bytes(ip, 'utf-8')                                      #- 3 periods for 4 octets
        for octet in ip.split('.'):                                     #- Each octet between 1 and three digits
            if len(octet) > 3 or len(octet) < 1:                        #- Each octet no greater than 255 or less than 0
                print('Bad octet in ip: {0}'.format(rawip))             #- No characters in string other than [0-9.]
                return False
            elif int(octet) > 255 or int(octet) < 0:
                print('Bad octet in ip: {0}'.format(rawip))
                return False

        if ip.count('.') != 3:
            print('Wrong number of octets in ip: {0}'.format(rawip))
            return False

        for char in re.findall(r'[^0-9.]',ip):
            print('Bad character {0} in ip: {1}'.format(char, rawip))
            return False

        return True

    def sort(self, ip, bin_ip):
        bin_ip = int(bin_ip, 2)
        sorted = False
        subndict = netbox_prefixes()
        for prefix in subndict:
            if bin_ip >= int(subndict[prefix]['lower'], 2) and bin_ip <= int(subndict[prefix]['upper'], 2):
                sorted = True
                return prefix
        
        if not sorted:
            return '.'.join(ip.split('.')[:3]) + '.0/24'


def valid_ip(ip):                                             #Requirements for validity:
    rawip = bytes(ip, 'utf-8')                                      #- 3 periods for 4 octets
    for octet in ip.split('.'):                                     #- Each octet between 1 and three digits
        if len(octet) > 3 or len(octet) < 1:                        #- Each octet no greater than 255 or less than 0
            print('Bad octet in ip: {0}'.format(rawip))             #- No characters in string other than [0-9.]
            return False
        elif int(octet) > 255 or int(octet) < 0:
            print('Bad octet in ip: {0}'.format(rawip))
            return False

    if ip.count('.') != 3:
        print('Wrong number of octets in ip: {0}'.format(rawip))
        return False

    for char in re.findall(r'[^0-9.]',ip):
        print('Bad character {0} in ip: {1}'.format(char, rawip))
        return False

    return True


def binary_ip(ip):
    bin_ip = ''
    for octet in ip.split('.'):
        bin_ip += bin(int(octet))[2:].zfill(8) 
    #strip 0b prefix and pad to size with 0s
    return bin_ip


def subn_bounds(subnet):
    bounds = {}

    ip = subnet.split('/')[0]   #prefixes come in form x.x.x.x/mask
    lower = binary_ip(ip)
    bounds['lower'] = lower

    mask = int(subnet.split('/')[1])

    upper = str(lower)
    upper = upper[:mask]
    for i in range(32 - mask):
        i = i   #stop vscode showing a warning for unused var
        upper += '1'    #set all bits out of mask range
    bounds['upper'] = upper

    return bounds


def netbox_prefixes():
    prefixes = {}
    with open('Sources/prefixes.txt') as stream:
        for line in stream.read().splitlines():
            if line not in prefixes:
                prefixes[line] = subn_bounds(line)
    return prefixes


def netbox_sort(ip):
    bin_ip = int(binary_ip(ip), 2)
    sorted = False
    subndict = netbox_prefixes()
    for prefix in subndict:
        if bin_ip >= int(subndict[prefix]['lower'], 2) and bin_ip <= int(subndict[prefix]['upper'], 2):
            sorted = True
            return prefix
    
    if not sorted:
        # print('No prefix match for ip {0}. Sorted using default method...'.format(ip))
        return '.'.join(ip.split('.')[:3]) + '.0/24'


def in_subnet(ip, subnet, verbose=False):
    bin_ip = int(binary_ip(ip), base=2)
    bounds = subn_bounds(subnet)
    if bin_ip >= int(bounds['lower'],2) and bin_ip <= int(bounds['upper'],2):
        if verbose:
            print('IP Address {0} is within subnet {1}.'.format(ip, subnet))
        return True
    else:
        if verbose:
            print('IP Address {0} is outside subnet {1}.'.format(ip, subnet))
        return False
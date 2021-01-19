import re

def valid_ip(string):
    rawstring = bytes(string, 'utf-8')
    for octet in string.split('.'):
        if len(octet) > 3 or len(octet) < 1:
            print('Bad octet in ip: {0}'.format(rawstring))
            return False
        elif int(octet) > 255 or int(octet) < 0:
            print('Bad octet in ip: {0}'.format(rawstring))
            return False

    if string.count('.') != 3:
        print('Wrong number of octets in ip: {0}'.format(rawstring))
        return False

    for char in re.findall(r'[^0-9.]',string):
        print('Bad character {0} in ip: {1}'.format(char, rawstring))
        return False

    return True


def subn_bounds(subnet):
    bounds = {}

    ip = subnet.split('/')[0]   #prefixes come in form x.x.x.x/mask
    lower = binaryip(ip)
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
    with open('../sources/prefixes.txt') as stream:
        for line in stream.read().splitlines():
            if line not in prefixes:
                prefixes[line] = subn_bounds(line)
    return prefixes


def netbox_sort(ip):
    bin_ip = int(binaryip(ip), 2)
    sorted = False
    subndict = netbox_prefixes()
    for prefix in subndict:
        if bin_ip >= int(subndict[prefix]['lower'], 2) and bin_ip <= int(subndict[prefix]['upper'], 2):
            sorted = True
            return prefix
    
    if not sorted:
        # print('No prefix match for ip {0}. Sorted using default method...'.format(ip))
        return '.'.join(ip.split('.')[:3]) + '.0/24'


def binaryip(ip):
    bin_ip = ''
    for octet in ip.split('.'):
        bin_ip += bin(int(octet))[2:].zfill(8) 
       #strip 0b prefix and pad to size with 0s
    return bin_ip


def in_subnet(ip, subnet, verbose=False):
    bin_ip = int(binaryip(ip), base=2)
    bounds = subn_bounds(subnet)
    if bin_ip >= int(bounds['lower'],2) and bin_ip <= int(bounds['upper'],2):
        if verbose:
            print('IP Address {0} is within subnet {1}.'.format(ip, subnet))
        return True
    else:
        if verbose:
            print('IP Address {0} is outside subnet {1}.'.format(ip, subnet))
        return False
import re
from binary import in_subnet

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

def foreign_ip(ip):
    if in_subnet(ip, '192.168.0.0/16') or in_subnet(ip, '10.0.0.0/8') or ip.in_subnet(ip, '172.16.0.0/12'):
        print('Private IP address {0} found.'.format(ip))
        return False
    elif in_subnet(ip, '103.127.18.0/24') or in_subnet(ip, '119.63.219.0/24'): #check this is the right subnet
        print('Managed IP address {0} found.'.format(ip))
        return False
    else:
        return True
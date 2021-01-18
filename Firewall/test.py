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
import csv
import pprint

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
    with open('../sources/prefixes.csv') as stream:
        for row in csv.reader(stream):
            if row[0] not in prefixes:
                prefixes[row[0]] = subn_bounds(row[0])
    return prefixes

def binaryip(ip):
    bin_ip = ''
    for octet in ip.split('.'):
        bin_ip += bin(int(octet))[2:].zfill(8) 
       #strip 0b prefix and pad to size with 0s
    return bin_ip

# if __name__ == '__main__':
#     pprint.pprint(netbox_prefixes())
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

def netbox_sort(ip):
    bin_ip = int(binaryip(ip), 2)
    sorted = False
    subndict = netbox_prefixes()
    for prefix in subndict:
        if bin_ip > int(subndict[prefix]['lower'], 2) and bin_ip < int(subndict[prefix]['upper'], 2):
            sorted = True
            return prefix
    
    if not sorted:
        print('No prefix match for ip {0}. Sorted using default method...'.format(ip))
        return '.'.join(ip.split('.')[:3]) + '.0/24'

def binaryip(ip):
    bin_ip = ''
    for octet in ip.split('.'):
        bin_ip += bin(int(octet))[2:].zfill(8) 
       #strip 0b prefix and pad to size with 0s
    return bin_ip

# if __name__ == '__main__':
#     pprint.pprint(netbox_prefixes())
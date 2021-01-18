import re, os
import binary

def main():
    master = []
    with open('J:/atemp/wellington/block_ips.txt', 'r') as stream:
        for line in stream.readlines():
            if not line.startswith('#'):
                cleanline = re.sub(r'[^0-9.]','',line)
                if line.strip('\n \t') != cleanline:
                    print('Unexpected chars in line: "{0}"'.format(bytes(line, 'utf-8')))
                master.append(cleanline)
    fq_mtime = 0
    br_mtime = 0
    for file in os.scandir('J:/atemp/wellington'):
        if 'forti-quarantine' in file.name and file.stat().st_mtime > fq_mtime:
            fq_latest = file
            fq_mtime = file.stat().st_mtime
        elif 'block-range' in file.name and file.stat().st_mtime > br_mtime:
            br_latest = file
            br_mtime = file.stat().st_mtime
    master = forti_addips(master, fq_latest)
    master = forti_addips(master, br_latest)

    master = list(dict.fromkeys(master))
    test(master)

    with open('log.txt', 'w') as log:
        for ip in master:
            log.write(ip + '\n')

def forti_addips(list, file):
    with open(file, 'r') as stream:
        for line in stream.readlines():
            if len(line) >= 7 and line.count('.') >= 3 and len(re.findall(r'[0-9]',line)) >= 4:
                ip = line.split()[0]
                cleanip = re.sub(r'[^0-9.]','',ip)
                if ip != cleanip:
                    print('Unexpected chars in string: "{0}"'.format(bytes(ip, 'utf-8')))
                list.append(cleanip)
    return list

def test(list):
    for i in range(len(list)):
        item = list[i]
        bad = False
        for octet in item.split('.'):
            if len(octet) > 3 or len(octet) < 1:
                print('Bad octet in ip: "{0}"'.format(bytes(item, 'utf-8')))
                bad = True
            elif int(octet) > 255 or int(octet) < 0:
                print('Bad octet in ip: "{0}"'.format(bytes(item, 'utf-8')))
                bad = True

        if item.count('.') != 3:
            print('Too many octets in ip: "{0}"'.format(bytes(item, 'utf-8')))
            bad = True

        if not bad:
            if binary.test(item, '192.168.0.0/16') or binary.test(item, '10.0.0.0/8') or binary.test(item, '172.16.0.0/12'):
                print('Private IP address {0} found.'.format(item))
                bad = True
            elif binary.test(item, '103.127.18.0/24') or binary.test(item, '119.63.219.0/24'): #check this is the right subnet
                print('Managed IP address {0} found.'.format(item))
                bad = True

        if bad:
            list.pop(i)

if __name__ == "__main__":
    main()
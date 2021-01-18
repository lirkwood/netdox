import re, os
import binary
import requests

def main():
    master = []
    global rejects
    rejects = []
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
    master = addips(master, fq_latest)
    master = addips(master, br_latest)

    master = list(dict.fromkeys(master))
    test(master)

    master.insert(0, '#Block_IPs')
    master.insert(1, '#New IPs taken from: {0} and {1}'.format(fq_latest.path, br_latest.path))
    for item in rejects:
        master.insert(2, '#Rejected ip: ' + item)

    with open('log.txt', 'w') as log:
        for line in master:
            log.write(line + '\n')
    
    update()

def addips(list, file):
    with open(file, 'r') as stream:
        for line in stream.readlines():
            if len(line) >= 7 and line.count('.') >= 3 and len(re.findall(r'[0-9]',line)) >= 4:
                ip = line.split()[0]
                cleanip = re.sub(r'[^0-9.]','',ip)
                if ip != cleanip:
                    print('Unexpected chars in string: "{0}". Skipping...'.format(bytes(ip, 'utf-8')))
                    rejects.append(ip)
                else:
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
            rejects.append(item)

def update():
    url = 'https://sy4-storage-03.allette.com.au:9000/fortigate/test.txt'
    header = {'content-type': 'application/x-www-form-urlencoded'}
    with open('log.txt','rb') as payload:
        r = requests.put(url, data=payload, headers=header)
        print(r.text)


if __name__ == "__main__":
    main()
import re, os
import requests
import iptools

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
    # fq_mtime = 0
    # br_mtime = 0
    # for file in os.scandir('J:/atemp/wellington'):
    #     if 'forti-quarantine' in file.name and file.stat().st_mtime > fq_mtime:
    #         fq_latest = file
    #         fq_mtime = file.stat().st_mtime
    #     elif 'block-range' in file.name and file.stat().st_mtime > br_mtime:
    #         br_latest = file
    #         br_mtime = file.stat().st_mtime
    master = addips(master, 'J:/atemp/wellington/block-range-21-Jan.txt')
    master = addips(master, 'J:/atemp/wellington/forti-quarantine-21-Jan.txt')
    master = addips(master, 'talos.txt')

    seen = []
    dupes = []
    for ip in master:
        if ip not in seen:
            seen.append(ip)
        else:
            dupes.append(ip)
    
    with open('dupes.txt','w') as log:
        for ip in dupes:
            log.write(ip +'\n')

    master = list(dict.fromkeys(master))

    for i in range(len(master)):
        ip = iptools.parsed_ip(master[i])
        if not ip.valid:
            rejects.append(ip)
            master.pop(i)
        elif not ip.foreign:
            rejects.append(ip)
            master.pop(i)

    master.insert(0, '#Block_IPs')
    # master.insert(1, '#New IPs taken from: {0} and {1}'.format(fq_latest.path, br_latest.path))
    for item in rejects:
        master.insert(2, '#Rejected ip: ' + item)

    with open('block_ips.txt', 'w') as log:
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

def update():
    url = 'https://sy4-storage-03.allette.com.au:9000/fortigate/block_ips.txt'
    header = {'content-type': 'application/x-www-form-urlencoded'}
    with open('block_ips.txt','rb') as payload:
        r = requests.put(url, data=payload, headers=header)
        with open('log.txt','w') as log:
            log.write(r.text)


if __name__ == "__main__":
    main()
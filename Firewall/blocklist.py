import re, os
import requests
import datetime
import iptools
import talos

url = 'https://sy4-storage-03.allette.com.au:9000/fortigate/block_ips.txt'

def main():
    master = []
    count = {}
    global rejects
    rejects = []

    blockrange = 'J:/atemp/wellington/block-range-14-Feb.txt'
    quarantine = 'J:/atemp/wellington/forti-quarantine-15-Feb.txt'
    
    current = requests.get(url)
    for line in str(current.content, encoding='utf-8').split('\r\n'):
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
    count['old'] = len(master)
    master = addips(master, blockrange)
    count['blockrange'] = len(master) - count['old']
    master = addips(master, quarantine)
    count['quarantine'] = len(master) - ( count['old'] + count['blockrange'] )
    master = addips(master, 'talos_clean.txt')
    count['talos'] = len(master) - ( count['old'] + count['blockrange'] + count['quarantine'] )

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

    tmp = []
    for i in range(len(master)):
        ip = iptools.parsed_ip(master[i])
        if not ip.valid:
            if not ip.string.isspace():
                rejects.append(ip.string)
        elif not ip.foreign:
            if not ip.string.isspace():
                rejects.append(ip.string)
        else:
            tmp.append(master[i])
    
    master = list(tmp)

    master.insert(0, '#Block_IPs')
    master.insert(1, '#Processed at time '+ str(datetime.datetime.utcnow()) +' +1100 UTC')
    master.insert(2, '#{0} ips in blocklist.'.format(len(master)))
    master.insert(2, '#{0} new ips added total.'.format(len(master) - count['old']))
    master.insert(2, '#{0} ips from previous block_ips.txt'.format(count['old']))
    master.insert(3, '#{0} ips from {1}'.format(count['blockrange'], blockrange))
    master.insert(4, '#{0} ips from {1}'.format(count['quarantine'], quarantine))
    master.insert(5, '#{0} ips from Talos.'.format(count['talos']))
    for item in rejects:
        print('Rejected ip: ' + item)

    with open('block_ips.txt', 'w') as log:
        for line in master:
            log.write(line + '\n')
    
    update()

def addips(iplist, file):
    with open(file, 'r') as stream:
        for line in stream.readlines():
            if len(line) >= 7 and line.count('.') >= 3 and len(re.findall(r'[0-9]',line)) >= 4:
                ip = line.split()[0]
                cleanip = re.sub(r'[^0-9.]','',ip)
                if ip != cleanip:
                    print('Unexpected chars in string: "{0}". Skipping...'.format(bytes(ip, 'utf-8')))
                    rejects.append(ip)
                else:
                    iplist.append(cleanip)
    return list(dict.fromkeys(iplist))

def update():
    header = {'content-type': 'application/x-www-form-urlencoded'}
    with open('block_ips.txt','rb') as payload:
        r = requests.put(url, data=payload, headers=header)
        with open('log.txt','w') as log:
            log.write(r.text)


if __name__ == "__main__":
    main()
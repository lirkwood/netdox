import requests
import re
import pprint

def push():
    new = []
    with open('new.txt', 'r') as stream:
        for line in stream:
            new.append(line.strip('\n'))

    url = 'https://sy4-storage-03.allette.com.au:9000/fortigate/block_ips.txt'
    r = re.sub(r'[^0-9./]',';',requests.get(url).text).split(';')
    l = list(dict.fromkeys(r + new))
    l = list(filter(None, l))
    l.insert(0, '#Block_IPs')
    pprint.pprint(l)

    stream = open('block_ips.txt', 'w+')
    for i in l:
        stream.write(i + '\n')
    stream.seek(0)
    data = stream.read()
    stream.close()
    
    header = {
        'Host': 'sy4-storage-03.allette.com.au:9000',
        'Content-Type': 'applicatiom/octet-stream'
    }
    requests.put(url, headers=header, data=data)

if __name__ == '__main__':
    push()
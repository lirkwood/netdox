import datetime
import requests
import hashlib
import base64
import hmac
import json
import csv

def request():
    with open('query.json', 'r') as stream:
        payload = json.load(stream)

        url = "https://graylogiv.allette.com.au/api/views/search/sync"

        headers = {
        'Accept': 'application/json',
        'X-Requested-By': 'cli',
        'Content-Type': 'application/json',
        'Authorization': 'Basic MTRudnRlOTgwNGl2bnBydjJ0MmlxczM3dDRvbmU2Nm8xZWdycnQ3Z2VrNGRrZTg2amNsZjp0b2tlbg=='
        }

        response = requests.post(url, headers=headers, data=json.dumps(payload))

        rtext = json.loads(response.text)
        return rtext
    

def parse():
    global ip
    global domain
    iplist = {}
    with open('response.json', 'r') as stream:
        jsondata = json.load(stream)
        k1 = 'bbd5228d-dbad-4efa-a19e-bacb73b7530f' #the two ids used for the search
        k2 = 'd69f2b53-a812-454a-9f9d-0786d8fccaa6'

        try:
            messages = jsondata['results'][k1]['search_types'][k2]['messages']
            for message in messages:
                m = message['message']['message']
                ip = getcontent(m)
                iplist[ip] = domain

        except KeyError:
            print('No messages returned')

    return iplist
            
def getcontent(s):
    global domain
    s = s.split('warning: hostname ')[1]
    s = s.split(':')[0]
    s = s.split(' ')
    domain = s[0]
    return s[-1]


def main():
    response = request()
    with open('response.json', 'w') as stream:
        stream.write(json.dumps(response, indent=4))
    
    iplist = parse()

    with open('ip.csv', 'w', newline='') as stream:
        blocklist = []
        # url = 'https://sy4-storage-03.allette.com.au:9000/fortigate/block_ips.txt'
        # for line in requests.get(url).text.split('\n'):
        # #     if '#' not in line:
        #     blocklist.append(line)
        
        writer = csv.writer(stream)
        for ip in iplist:
            ipcomp = ip.split('.')
            if ip in blocklist:
                pass
            elif ipcomp[0] == '172' or ipcomp[0] == '10':
                pass
            elif '.'.join(ipcomp[:2]) == '192.168':
                pass
            elif '.'.join(ipcomp[:3]) == '103.127.18' or '.'.join(ipcomp[:3]) == '127.0.0.1':
                pass
            else:
                writer.writerow([ip, iplist[ip]])

if __name__ == '__main__':
    main()

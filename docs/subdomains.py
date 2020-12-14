import re
import os
import json
import pprint
from bs4 import BeautifulSoup

def main():
    global master
    master = []
    idlist = []
    with open('../Sources/records.xml', 'r') as rstream:
        soup = BeautifulSoup(rstream, 'lxml')
        for record in soup.find_all('data'):
            if clean(record.type.string) == 'A':
                if not record.find('name').string:
                    idlist.append(clean(record.sourceid.string))
    for file in os.scandir('../Sources/records'):
        with open(file, 'r') as stream:
            jsondata = json.load(stream)
            for record in jsondata:
                if record['RecordType'] == 'A':
                    distname = record['DistinguishedName'].split(',')
                    if distname[0] == 'DC=@':  #if subdomain is @ then it is primary domain
                        name = distname[1].replace('DC=', '')
                        master.append(name)
    
    findom(idlist)

    with open('../Sources/pdomains.txt', 'w') as o:
        master = list(dict.fromkeys(master))
        master.sort(key=len, reverse=True)
        for i in master:
            o.write(i + '\n')


def findom(l):
    global master
    with open('../Sources/domains.xml', 'r') as dstream:
        soup = BeautifulSoup(dstream, 'lxml')
        idlist = list(dict.fromkeys(l))
        for id in idlist:
            record = soup.find('id', text=id).parent
            domain = clean(record.find('name').string)
            master.append(domain)

def clean(s):
    if s:
        s = re.sub(r'[^A-Za-z0-9-_.]+', '', s)
    return s

if __name__ == '__main__':
    main()

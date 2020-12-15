from bs4 import BeautifulSoup
import json
import csv
import os

def ad():
    global acount
    acount = 0
    for file in os.scandir('../Sources/records'):
        with open(file, 'r') as stream:
            jsondata = json.load(stream)
            for record in jsondata:
                if record['RecordType'] == 'A' or record['RecordType'] == 'CNAME':
                    acount += 1
    print(str(acount) + ' domains discovered from Active Directory')

def dnsme():
    global dcount
    dcount = 0
    with open('../Sources/records.xml', 'r') as stream:
        soup = BeautifulSoup(stream, 'lxml')
        records = soup.find_all('data')
        for r in records:
            type = r.type.string.strip('\n \t')
            if type == 'A' or type == 'CNAME':
                dcount += 1
                with open('log.txt', 'a') as l:
                    l.write(r.id.string.strip('\n \t'))
                    l.write('\n')
    print(str(dcount) + ' subdomains discovered from DNSMadeEasy')
    
def kube():
    global kcount
    kcount = 0
    with open('../Sources/ingress.json', 'r') as stream:
        jsondata = json.load(stream)
        for c in jsondata:
            for record in jsondata[c]['items']:
                for rule in record['spec']['rules']:
                    if 'host' in rule:
                        kcount += 1
    print(str(kcount) + ' domains discovered from Kubernetes')

def final():
    global ad
    ad = 0
    global dnsme
    dnsme = 0
    global kube
    kube = 0
    with open('../Sources/domains.csv', 'r') as stream:
        for row in csv.reader(stream):
            if row[0] == 'Active Directory':
                ad += 1
            elif row[0] == 'DNSMadeEasy':
                dnsme += 1
            elif row[0] == 'Kubernetes':
                kube += 1
    print('Final csv contains:\n\t{0} domains from Active Directory\n\t{1} domains from DNSMadeEasy\n\t{2} domains from Kubernetes'.format(ad, dnsme, kube))

def compare():
    adiff = acount - ad
    ddiff = dcount - dnsme
    kdiff = kcount - kube
    
    print('Final csv missing {0} domains from AD, {1} domains from DNSME, {2} domains from Kube'.format(adiff, ddiff, kdiff))
    

def main():
    ad()
    dnsme()
    kube()
    final()
    compare()
    

if __name__ == '__main__':
    main()
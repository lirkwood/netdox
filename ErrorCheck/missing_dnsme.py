from bs4 import BeautifulSoup
import csv

count = 0
with open('../Sources/domains.xml', 'r') as dstream:
    with open('../Sources/records.xml', 'r') as rstream:
        with open('../Sources/domains.csv') as source:
            dsoup = BeautifulSoup(dstream, 'lxml')
            rsoup = BeautifulSoup(rstream, 'lxml')
            domains = []
            for row in csv.reader(source):
                domains.append(row[1])
            records = rsoup.find_all('data')
            for r in records:
                if r.type.string.strip('\n \t.') == 'CNAME':
                    sourceid = r.sourceid.string.strip('\n \t.')
                    for d in dsoup.find_all('data'):
                        if d.id.string.strip('\n \t.') == sourceid:
                            parent = d.find('name').string.strip('\n \t')
                    dest = r.find('name').string
                    if dest:
                        dest = dest.strip('\n \t')
                        if not dest.endswith('.'):
                            dest = dest + '.' + parent
                        else:
                            dest = dest.strip('.')
                    else:
                        dest = parent
                    
                    dest = dest.replace('www.', '')
                    if dest not in domains:
                        count += 1
                        domains.append(dest)
                        print(dest)

print(count)            
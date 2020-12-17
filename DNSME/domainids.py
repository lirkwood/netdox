import json
from bs4 import BeautifulSoup

def main():
    d = {}
    with open('C:/Users/linus/network-documentation/Sources/domains.xml', 'r') as stream:
        soup = BeautifulSoup(stream, 'lxml')
        for record in soup.find_all('data'):
            d[record.find('name').string] = record.id.string
    with open('domainids.json', 'w') as o:
        o.write(json.dumps(d, indent=4))

if __name__ == '__main__':
    main()
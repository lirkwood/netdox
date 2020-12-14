from bs4 import BeautifulSoup
import json

def search():
    with open('../Sources/nmap.xml', 'r') as nmapstream:
        with open('../Sources/doc_domains.json') as domainstream:
            soup = BeautifulSoup(nmapstream, 'lxml')
            domains = json.load(domainstream)
            for hostnametag in soup.find_all('hostname'):
                domain = hostnametag['name'].replace('.internal', '').lower()
                if domain in domains:
                    print(domain)

def main():
    search()

if __name__ == '__main__':
    main()
from datetime import datetime
from bs4 import BeautifulSoup
import requests
import pprint
import json
import auth
import sys


base = 'https://ps-doc.allette.com.au/ps/service/'
token = auth.token()

header = {
    'authorization': 'Bearer {0}'.format(token)
}

date = datetime.now().replace(microsecond=0) #drop unnecessary microseconds


def scan():
    docids = []
    with open('../sources/domains.json', 'r') as stream:
        domains = json.load(stream)
        for domain in domains:
            docids.append('_nd_' + domain.replace('.', '_'))
    
    docids = list(dict.fromkeys(docids))

    return docids


def set(docid):
    params = {
        'name': date
    }

    url = base + 'members/~lkirkwood/groups/~network-documentation/uris/{0}/versions'.format(docid)

    r = requests.post(url, headers=header, params=params)
    
    with open('Logs/autoversionlog.xml', 'w') as log:
        log.write(BeautifulSoup(r.text, 'lxml').prettify())

def geturis(folder):
    params = {
        'relationship': 'children',
        'pagesize': 9999
    }

    url = base + 'groups/~network-documentation/uris/{0}/uris'.format(urimap[folder])

    r = requests.get(url, headers=header, params=params)
    with open('Logs/urilist.xml', 'w') as log:
        log.write(BeautifulSoup(r.text, 'lxml').prettify())

def archive(docids):
    with open('Logs/urilist.xml', 'r') as stream:
        soup = BeautifulSoup(stream, 'lxml')
        for uri in soup.find_all('uri'):
            if uri['docid'] not in docids:
                url = base + 'members/~lkirkwood/groups/~network-documentation/uris/{0}/archive'.format(uri['docid'])
                r = requests.post(url, headers=header)
                with open('Logs/archivelog.xml', 'w') as log:
                    log.write(BeautifulSoup(r.text, 'lxml').prettify())

urimap = {
    'hosts': '36057',
    'ips': '36058',
    'ports': '19040',
    'ansiblejson': '24577',
    'documents': '5471'
}

if __name__ == "__main__":
    docids = scan()
    geturis('hosts')
    archive(docids)
    for docid in docids:
        set(docid)
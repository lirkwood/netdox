from datetime import datetime
from bs4 import BeautifulSoup
import requests
import pprint
import json
import auth
import sys


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
    
    for docid in docids:
        set(docid)


def set(docid):
    params = {
        'name': date
    }

    url = 'https://ps-doc.allette.com.au/ps/service/members/~lkirkwood/groups/~network-documentation/uris/{0}/versions'.format(docid)

    r = requests.post(url, headers=header, params=params)
    
    with open('Logs/autoversionlog.xml', 'w') as log:
        log.write(BeautifulSoup(r.text, 'lxml').prettify())

def geturis(folder):
    params = {
        'relationship': 'children'
    }

    url = 'https://ps-doc.allette.com.au/ps/service/groups/~network-documentation/uris/{0}/uris'.format(urimap[folder])

    r = requests.get(url, headers=header, params=params)
    with open('Logs/urilist.xml', 'w') as log:
        log.write(BeautifulSoup(r.text, 'lxml').prettify())

urimap = {
    'hosts': '36057',
    'ips': '36058',
    'ports': '19040',
    'ansiblejson': '24577',
    'documents': '5471'
}

if __name__ == "__main__":
    # scan()
    geturis('hosts')
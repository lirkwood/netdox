from datetime import datetime
from bs4 import BeautifulSoup
from requests import post
import json
import auth
import sys

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
    token = auth.token()
    header = {
        'authorization': 'Bearer {0}'.format(token)
    }

    date = datetime.now().replace(microsecond=0) #drop unnecessary microseconds
    params = {
        'name': date
    }

    url = 'https://ps-doc.allette.com.au/ps/service/members/~lkirkwood/groups/~network-documentation/uris/{0}/versions'.format(docid)

    r = post(url, headers=header, params=params)
    
    with open('Logs/versionlog.xml', 'w') as log:
        log.write(BeautifulSoup(r.text, 'lxml').prettify())

if __name__ == "__main__":
    scan()
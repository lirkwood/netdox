from datetime import datetime
from bs4 import BeautifulSoup
from requests import post
import auth
import sys

def set(folder):
    token = auth.token()
    header = {
        'authorization': 'Bearer {0}'.format(token)
    }

    date = datetime.now().replace(microsecond=0) #drop unnecessary microseconds
    params = {
        'name': date
    }

    uri = urimap[folder]
    url = 'https://ps-doc.allette.com.au/ps/service/members/~lkirkwood/groups/~network-documentation/uris/{0}/versions'.format(uri)

    r = post(url, headers=header, params=params)
    
    with open('Logs/versionlog.xml', 'w') as log:
        log.write(BeautifulSoup(r.text, 'lxml').prettify())


urimap = {
    'Hosts': '32280',
    'IPs': '32879',
    'Ports': '19040',
    'AnsibleJson': '24577',
    'Documents': '5471'
}

if __name__ == "__main__":
    folder = sys.argv[1]
    set(folder)
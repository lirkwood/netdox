from bs4 import BeautifulSoup
import requests
import auth


token = auth.token()
header = {
    'authorization': 'Bearer {0}'.format(token)
}
base = 'https://ps-doc.allette.com.au/ps/service'

urimap = {
    'dns': 	'42416',
    'ips': '45604',
    'deployments': '42262',
    'xo': '42183'
}
global count
count = 0
dead = {}

def uris(folder):
    service = '/groups/~network-documentation/uris/{0}/uris'.format(urimap[folder])
    r = requests.get(base+service, headers=header, params={'pagesize': 9999})
    soup = BeautifulSoup(r.text, features='xml')
    for uri in soup.find_all('uri'):
        fragments(uri['docid'])


def fragments(uri):
    global count
    service = '/members/~lkirkwood/groups/~network-documentation/uris/{0}/fragments/{1}'.format(uri,'aliases')
    r = requests.get(base+service, headers=header)
    soup = BeautifulSoup(r.text, features='xml')
    
    for property in soup.find_all('property'):
        link = property['value']
        print('Testing '+ link)
        count += 1
        try:
            r = requests.get(link)
            if r.status_code > 400 and r.status_code < 600:
                print('Bad response code {0} from url {1}\n\n'.format(r.status_code, link))
                dead[link] = r.status_code
            else:
                print('OK\n\n')
                return True
        except Exception as e:
            print('Fatal error occurred: {0}\n\n'.format(str(e)))
            dead[link] = str(e)
    

def alive(url):
    r = requests.get(url)
    if r.status_code > 400 and r.status_code < 600:
        print('Bad response code {0} from url {1}\n\n'.format(r.status_code, url))
        return False
    else:
        print('OK\n\n')
        return True


if __name__ == "__main__":
    # alive('https://ps-doc.allette.com.au/ps/ui/g/network-documentation/d/42195.html')
    uris('dns')
    with open('log.txt','w') as log:
        log.write('Out of {0} tested urls, {1} failed.\n'.format(count, len(dead)))
        for url in dead:
            log.write('URL: {0} Code: {1}\n'.format(url, dead[url]))
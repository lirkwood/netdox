from bs4 import BeautifulSoup
import subprocess
import requests
import json
import auth
import os


token = auth.token()
header = {
    'authorization': 'Bearer {0}'.format(token)
}
base = 'https://ps-doc.allette.com.au/ps/service'

urimap = {
    'dns': 	'46055',
    'ips': '45604',
    'deployments': '42262',
    'xo': '42183'
}

urls = []   #list of urls to be tested

global count    #no. of urls tested
count = 0  
live = []      #no. of successful responses to a basic GET
dead = {}       #key = url, value = error code

def main(folder):
    get_uris(folder)

    for url in urls:
        test(url)

    with open('log.txt','w') as log:
        log.write('Out of {0} tested urls, {1} failed.\n'.format(count, len(dead)))
        for url in dead:
            log.write('URL: {0} Code: {1}\n\n'.format(url, dead[url]))
    with open('live.json','w') as out:
        out.write(json.dumps(live, indent=2))
    
    if not os.path.exists('outgoing'):
        os.mkdir('outgoing')
    else:
        for file in os.scandir('outgoing'):
            os.remove(file)
            
    subprocess.run('node screenshot.js')    #get screenshots of all urls in live

    for file in os.scandir('outgoing'):
        docid = '_nd_'+ file.name.split('.')[0]
        print(docid)


def get_uris(folder): #returns list of uris of all documents in a folder, defined by urimap
    service = '/groups/~network-documentation/uris/{0}/uris'.format(urimap[folder])
    r = requests.get(base+service, headers=header, params={'pagesize': 9999})
    soup = BeautifulSoup(r.text, features='xml')
    for document in soup.find_all('uri'):
        url = 'https://'+ document['docid'].replace('_nd_','').replace('_','.')
        urls.append(url)
    
        

def test(url):
    global count
    count += 1
    print('Testing '+ url)
    try:
        alive(url)
    except Exception as e:
        if '_ssl.c:1123' in str(e) and 'https' in url:
            try:
                if alive(url.replace('https','http')):
                    print('HTTPS failed but HTTP succeeded.\n\n')
                    dead[url] = 'HTTPS failed but HTTP succeeded.'
            except Exception as e:
                print('Fatal error occurred: {0}\n\n'.format(str(e)))
                dead[url] = str(e)
        else:
            print('Fatal error occurred: {0}\n\n'.format(str(e)))
            dead[url] = str(e)


def alive(url):
    r = requests.get(url, timeout=3)
    if r.status_code > 400 and r.status_code < 600:
        print('Bad response code {0} from url {1}\n\n'.format(r.status_code, url))
        dead[url] = r.status_code
    else:
        print('OK\n\n')
        live.append(url)
        return True




if __name__ == "__main__":
    main('dns')
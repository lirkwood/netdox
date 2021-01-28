from bs4 import BeautifulSoup
from datetime import datetime
from PIL import Image
import subprocess
import requests
import shutil
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
    'k8s': '47002',
    'xo': '42183'
}

live = []      #no. of successful responses to a basic GET
dead = {}       #key = url, value = error code


def main(folder):
    # urls, docids = get_uris(folder) 

    # version(folder, docids)
    
    urls, docids = get_uris(folder)     #get current uri list

    count = 0
    for url in urls:
        page = webpage(url)
        if not page.exclude:
            count += 1
            print('Testing '+ page.url)
            if page.test():
                live.append(page.url)
            else:
                if page.protocol == 'https' and '_ssl.c:1123' in str(page.code):
                    page.protocol = 'http'
                    if page.test():
                        dead['https://'+ page.domain] = 'HTTPS failed but HTTP succeeded.'
                        print('HTTPS failed but HTTP succeeded.\n\n')
                        live.append(page.url)
                    else:
                        dead[page.url] = str(page.code)
                        testips(page)
                else:
                    dead[page.url] = str(page.code)
                    testips(page)


    with open('log.txt','w') as log:
        log.write('Out of {0} tested urls, {1} failed.\n'.format(count, len(dead)))
        for url in dead:
            log.write('URL: {0} Code: {1}\n\n'.format(url, dead[url]))

    with open('live.json','w') as out:
        out.write(json.dumps(live, indent=2))   #write results to files
    
    for folder in ('screenshots', 'review'):    # clean screenshot dirs
        if not os.path.exists(folder):
            os.mkdir(folder)
        else:
            for file in os.scandir(folder):
                os.remove(file)
            
    subprocess.run('node screenshot.js')    #get screenshots of all urls in live

    imgdiff()

    for url in dead:  #copy placeholder for all docs with no image 
        docid = '_nd_img_'+ url.split('://')[1].replace('.','_')
        shutil.copy('placeholder.png', 'screenshots/{0}.png'.format(docid))

    subprocess.run('java -jar c:/saxon/saxon-he-10.3.jar -xsl:status.xsl -s:review.xml -o:_nd_status_update.psml')


def get_uris(folder): #returns list of uris of all documents in a folder, defined by urimap
    urls = []
    docids = []
    service = '/groups/~network-documentation/uris/{0}/uris'.format(urimap[folder])
    r = requests.get(base+service, headers=header, params={'pagesize': 9999})
    soup = BeautifulSoup(r.text, features='xml')
    for document in soup.find_all('uri'):
        docids.append(document['docid'])
        url = 'https://'+ document['docid'].replace('_nd_','').replace('_','.')
        urls.append(url)
    
    return urls, docids


def version(folder, docids):
    outgoing = []
    for file in os.scandir('../outgoing/'+ folder):
        outgoing.append('_nd_'+ file.name.replace('.psml',''))

    for docid in docids:    #archive docs not generated in last batch
        if docid not in outgoing:
            archive(docid)
    
    service = '/members/~lkirkwood/groups/~network-documentation/uris/{0}/versions'.format(urimap[folder])
    requests.post(base+service, headers=header, params={'name': datetime.now().replace(microsecond=0)})   # version all docs that are not archived => current


def archive(docid):
    service = '/members/~lkirkwood/groups/~network-documentation/uris/{0}/archive'.format(docid)
    r = requests.post(base+service, headers=header)
    return r


def testips(page):
    for ip in page.get_ips():
        ping = subprocess.run('ping -n 1 '+ ip, stdout=subprocess.PIPE)
        if ping.returncode == 0 and 'Destination host unreachable' not in str(ping.stdout):
            print('URL {0} failed but ip {1} succeeded.\n\n'.format(page.url, ip))
            dead[page.url] += '\nIP {0} succeeded. Tested for URL {1}.'.format(ip, page.url)
        else:
            print('URL {0} failed and ip {1} failed with code {2}.\n\n'.format(page.url, ip, ping.returncode))
            dead[page.url] += '\nIP {0} failed. Tested for URL {1}.'.format(ip, page.url)


def imgdiff():
    with open('review.xml','w') as stream:
        stream.write('<root>')
        review = []
        for file in os.scandir('screenshots'): #test if current screenshot = known screenshot
            result = subprocess.run('imgdiff -t 0.3 base/{0} screenshots/{0}'.format(file.name), stderr=subprocess.PIPE)
            if result.returncode != 0:
                review.append(file.name)
                if 'cannot find the file' in str(result.stderr):
                    shutil.copyfile('screenshots/'+ file.name, 'review/'+ file.name)    
                else:
                    src = Image.open('base/'+ file.name)
                    src.resize((1024, 576))
                    new = Image.open('screenshots/'+ file.name)
                    new.resize((1024, 576))
                    combined = Image.new('RGB',(src.size[0]*2, src.size[1]))
                    combined.paste(src,(0,0))
                    combined.paste(new,(src.size[0],0))
                    combined.save('review/'+ file.name)
            img = Image.open('screenshots/'+ file.name)
            img.resize((1024, 576))
            os.remove('screenshots/'+ file.name)
            img.save('screenshots/'+ file.name)
        stream.write(json.dumps(review, indent=2))
        stream.write('</root>')


exclusions = open('exclusions.txt','r').read().splitlines()
settings = json.load(open('settings.json','r'))

class webpage:
    def __init__(self, url):
        self.domain = url.split('://')[1]
        self.docid = '_nd_'+ self.domain.replace('.','_')
        
        if self.domain in settings:     #get settings
            if 'protocol' in settings[self.domain]:
                self._protocol = settings[self.domain]['protocol']
            else:
                self._protocol = url.split('://')[0]

            if 'auth' in settings[self.domain]:
                self.auth = settings[self.domain]['auth']
                self.url = '{0}://{1}:{2}@{3}'.format(self._protocol, self.auth['user'], self.auth['password'], self.domain)
            else:
                self.auth = None
        else:
            self._protocol = url.split('://')[0]
            self.auth = None

        self.url = self._protocol +'://'+ self.domain

        if url in exclusions:   #get exclusion details
            self.exclude = True
        else:
            self.exclude = False

    @property
    def protocol(self):
        return self._protocol
    
    @protocol.setter
    def protocol(self, new_protocol):
        if new_protocol == 'http' or new_protocol == 'https':
            self._protocol = new_protocol
            self.url = self._protocol +'://'+ self.domain
        else:
            print('Provide a valid protocol (http or https)')
    
    def test(self):
        try:
            r = requests.get(self.url, timeout=1)
            self.code = r.status_code
            if self.code > 400 and self.code < 600:
                print('Bad response code {0} from url {1}\n\n'.format(self.code, self.url))
                self.status = False
                return False
            else:
                print('OK\n\n')
                self.status = True
                return True
        except Exception as e:
            self.code = e
            print('Fatal error. \n\n')
            self.status = False
            return False

    def get_ips(self):
        self.ips = []

        service = '/members/~lkirkwood/groups/~network-documentation/uris/{0}/fragments/dest'.format(self.docid)
        soup = BeautifulSoup(requests.get(base+service, headers=header).text, 'lxml')
        for prop in soup.find_all('property'):
            if prop['name'] == 'ipv4':
                self.ips.append(prop.xref.string)
        
        return self.ips




if __name__ == "__main__":
    main('dns')
import os
import requests
from bs4 import BeautifulSoup


def post(section, docid, fragment, script=os.path.basename(__file__)):

    jsession = '1D06B42BF47D1CDE208CB8BFE119087B'

    title = 'Automated edit'
    content = 'Automated edit sent by ' + script + ' on fragment ' + fragment
    prefix = 'https://ps-doc.allette.com.au/ps/service/'
    group = 'network-documentation'
    member = 'lkirkwood'
    header = {
        'Cookie': 'JSESSIONID={0}'.format(jsession)
    }

    get = 'groups/~{0}/uris/~{1}/fragments/{2}/edits'.format( group, docid, fragment)

    getresponse = requests.get(prefix + get, headers=header)
    log(getresponse.text)
    rsoup = BeautifulSoup(getresponse.text, features='xml')

    
    for edit in rsoup.find_all('edit'):
        editid = edit['id']

    params = {
        'content': bytes(content, 'utf-8'),
        'title': bytes(title, 'utf-8')
    }

    try:
        post = 'members/~{0}/groups/~{1}/uris/~{2}/edits/{3}/notes'.format(member, group, docid, editid)

        getresponse = requests.post(prefix + post, headers=header, params=params)
        log(getresponse.text)
    except UnboundLocalError:
        print(docid + ' failed. No edit ids recieved: likely cannot find document.')

def log(s):
    logsoup = BeautifulSoup(s, features='xml')
    with open('Logs/editlog.xml', 'w') as o:
        o.write(logsoup.prettify())
    

if __name__ == '__main__':
    docid = '_nd_allette_com'
    section = 'details'
    fragment = 'kube'
    post(section, docid, fragment)

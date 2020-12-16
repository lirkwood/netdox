import auth
import requests
from bs4 import BeautifulSoup


def push(script, path, section, docid=None, fragment=None, prefix=None):

    token = auth.token()
    if '\\' in path:
        filename = path.split('\\')[-1]
    else:
        filename = path.split('/')[-1]

    if not docid:
        docid = filename.split(';')[0]

    if not fragment:
        fragment = filename.split(';')[1]

    stream = open(path, 'r')
    content = ''
    for i in stream:
        content += i
    global base
    base = 'https://ps-doc.allette.com.au/ps/service/'
    global member
    member = 'lkirkwood'
    global group
    group = 'network-documentation'
    global header
    header = {
        'authorization': 'Bearer {0}'.format(token)
    }
    params = {
        'section': section,
        'content': content,
        'note': 'Automated edit sent by ' + script + ' on fragment ' + fragment
    }
    if prefix:
        params['fragmentprefix'] = prefix
        fragment = prefix + '1'
    
    method = test(section, docid, fragment, prefix)

    if method == 'put':
        service = 'members/~{0}/groups/~{1}/uris/~{2}/fragments/{3}'.format(
            member, group, docid, fragment)
    elif method == 'post':
        service = 'members/~{0}/groups/~{1}/uris/~{2}/fragments'.format(
            member, group, docid)

    url = base + service

    if method == 'put':
        r = requests.put(url, headers=header, params=params)
    elif method == 'post':
        r = requests.post(url, headers=header, params=params)

    response = r.text

    with open('Logs/log.xml', 'w') as log:
        soup = BeautifulSoup(response, 'lxml')
        log.write(soup.prettify())
    return response


def test(section, docid, fragment, prefix):
    global base
    global group
    global header
    url = base + 'groups/~{0}/uris/~{1}/fragments/{2}/edits'.format(group, docid, fragment)
    r = requests.get(url, headers=header)
    soup = BeautifulSoup(r.text, 'lxml')
    if soup.find('error'):
        return 'post'
    else:
        return 'put'


if __name__ == '__main__':
    path = 'ansible/outgoing/_nd_alto_allette_com_au;ansible_mounts_xvda1;.psml'
    section = 'ansible'
    script = 'manual execution'
    r = push(script, path, section, prefix='test')

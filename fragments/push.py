import auth
import requests
from bs4 import BeautifulSoup


def put(script, path, section, docid='unset', fragment='unset'):
    return main('put', script, path, section, docid, fragment)


def post(script, path, section, docid='unset'):
    return main('post', script, path, section, docid)


def main(method, script, path, section, docid='unset', fragment='unset'):

    token = auth.token()
    if '\\' in path:
        filename = path.split('\\')[-1]
    else:
        filename = path.split('/')[-1]

    if docid == 'unset':
        docid = filename.split(';')[0]

    if fragment == 'unset':
        fragment = filename.split(';')[1]

    stream = open(path, 'r')
    content = ''
    for i in stream:
        content += i

    # print(content)
    # content = bytes(content, 'utf-8')

    prefix = 'https://ps-doc.allette.com.au/ps/service/'
    member = 'lkirkwood'
    group = 'network-documentation'
    header = {
        'authorization': 'Bearer {0}'.format(token)
    }
    params = {
        'section': section,
        'content': content,
        'note': 'Automated edit sent by ' + script + ' on fragment ' + fragment
    }
    if method == 'put':
        service = 'members/~{0}/groups/~{1}/uris/~{2}/fragments/{3}'.format(member, group, docid, fragment)
    elif method == 'post':
        service = 'members/~{0}/groups/~{1}/uris/~{2}/fragments'.format(member, group, docid)
    
    url = prefix + service

    if method == 'put':
        r = requests.put(url, headers=header, params=params)
    elif method == 'post':
        r = requests.post(url, headers=header, params=params)

    response = r.text

    with open('Logs/log.xml', 'w') as log:
        soup = BeautifulSoup(response, 'lxml')
        log.write(soup.prettify())
    return response


if __name__ == '__main__':
    path = 'ansible/outgoing/_nd_alto_allette_com_au;ansible_mounts_xvda1;.psml'
    docid = '_nd_testhost'
    section = 'ansible'
    script = 'manual execution'
    r = post(script, path, section, docid)
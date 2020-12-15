import os
import auth
import push
import requests
from bs4 import BeautifulSoup


def main():
    path = 'Ansible/outgoing'
    section = 'ansible'
    script = 'ansible_info.py'
    # dcount = {}
    # for file in os.scandir(path):
    #     docid = file.name.split(';')[0]
    #     if docid not in dcount:
    #         dcount[docid] = 0
    #     dcount[docid] += 1
    # # for docid in dcount:
    # #     delete(docid, dcount[docid], section)
    for file in os.scandir(path):
        filepath = path + '/' + os.path.basename(file)
        push.post(script, filepath, section)


# def delete(docid, count, section):
#     jession = 'JSESSIONID=FB00C026C59FFC5C6EA4C089A4BF8095'
#     for fragment in range(count):
#         url = 'https://ps-doc.allette.com.au/ps/service/members/~{0}/groups/~{1}/uris/~{2}/fragments/{3}/delete'.format('lkirkwood', 'network-documentation', docid, fragment)
#         r = requests.post(url, headers={'Cookie': jession}, params={'section': section})
#         with open('Logs/ansible_info.xml', 'w') as o:
#             o.write(BeautifulSoup(r.text, 'lxml').prettify())

if __name__ == '__main__':
    main()

import os
import auth
import push
import requests
from bs4 import BeautifulSoup


def main():
    path = 'Ansible/outgoing'
    section = 'ansible'
    script = 'ansible_info.py'
    for file in os.scandir(path):
        filepath = path + '/' + os.path.basename(file)
        push.put(script, filepath, section)

if __name__ == '__main__':
    main()

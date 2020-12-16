import os
import auth
import push_aware
import requests
from bs4 import BeautifulSoup


def main():
    path = 'Ansible/outgoing'
    section = 'ansible'
    script = 'ansible_info.py'
    for file in os.scandir(path):
        prefix = file.name.split(';')[1]
        filepath = path + '/' + os.path.basename(file)
        push_aware.push(script, filepath, section, prefix=prefix)

if __name__ == '__main__':
    main()

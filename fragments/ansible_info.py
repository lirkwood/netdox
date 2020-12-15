import os
import push
import requests

def main():
    path = 'Ansible/outgoing'
    section = 'ansible'
    for file in os.scandir(path):
        filepath = path + '/' + os.path.basename(file)
        push.post(filepath, section)

if __name__ == '__main__':
    main()
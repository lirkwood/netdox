from bs4 import BeautifulSoup
import json
import csv
import os

import ansible.ansible
import ansible_info

import reversedns.get_ptr
import ptr_info

print('Generating Ansible fragments...')
print('****************************')
ansible.ansible.main()
print('******************************* \n\n')
print('Generating reverse dns record fragments...\n\n')
reversedns.get_ptr.main()

print('Pushing Ansible fragments...')
ansible_info.main()
print('Pushing reverse dns record fragments...')
ptr_info.main()

print('Done.')

import iptools
import re

with open('talos.txt','r') as stream:
    with open('talos_clean.txt','w') as output:
        for line in stream.read().splitlines():
            match = re.match(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', line)
            if match:
                if iptools.valid_ip(match[0]):
                    output.write(line.split()[0] +'\n')
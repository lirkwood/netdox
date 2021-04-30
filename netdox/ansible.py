from paramiko import client, AutoAddPolicy
from icinga_inf import icinga_hosts

## Main functions

def exec(cmd):
    sshclient = client.SSHClient()
    sshclient.set_missing_host_key_policy(AutoAddPolicy())
    sshclient.connect('ansiblesy4.allette.com.au', username='root', key_filename='src/ssh/ssh-privatekey')
    stdin, stdout, stderr = sshclient.exec_command(cmd)
    stdin.close()
    stdout = str(stdout.read(), encoding='utf-8')
    stderr = str(stderr.read(), encoding='utf-8')
    return (stdout, stderr)

def playbook(path, tags=[], vars={}):
    # encode dict as extra vars
    varstring = ''
    for key in vars:
        if not varstring:
            varstring = '-e "'
        else:
            varstring += ' '

        value=vars[key]
        varstring += f'{key}={value}'
    if varstring: varstring += '"'

    # encode list as quoted csv
    tagstring = ''
    for tag in tags:
        if not tagstring:
            tagstring += '--tags "'
        else:
            tagstring += ', '
        tagstring += tag
    if tagstring: tagstring += '"'

    return exec(f'ansible-playbook {path} {tagstring} {varstring}')


## Functions for specific plays

def icinga_add_generic(address, location=None, icinga=None, display_name=None):
    if not location and not icinga:
        raise ValueError('[ERROR][ansible.py] Either location or icinga must be defined.')
    elif location and not icinga:
        for host in icinga_hosts:
            if location == icinga_hosts[host]['location']:
                icinga = host
        if not icinga:
            raise ValueError('[ERROR][ansible.py] Unrecognised location {location}')
            
    tags = ['add-generic']
    vars = {
        "icinga": icinga,
        "host": address
        }
    if display_name:
        vars['display_name'] = display_name
    else:
        vars['display_name'] = address
    
    return playbook('/etc/ansible/icinga.yml', tags, vars)
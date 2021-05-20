from paramiko import client, AutoAddPolicy
import utils

icinga_hosts = utils.auth['icinga']

## Main functions

def exec(cmd):
    """
    Executes a command on the ansible machine
    """
    sshclient = client.SSHClient()
    sshclient.set_missing_host_key_policy(AutoAddPolicy())
    sshclient.connect('ansiblesy4.allette.com.au', username='root', key_filename='src/ssh/ssh-privatekey')
    stdin, stdout, stderr = sshclient.exec_command(cmd)
    stdin.close()
    stdout = str(stdout.read(), encoding='utf-8')
    stderr = str(stderr.read(), encoding='utf-8')
    return (stdout, stderr)

def playbook(path, tags=[], vars={}):
    """
    Runs a playbook with optional tags and extra vars
    """
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

    stdout, stderr = exec(f'ansible-playbook {path} {tagstring} {varstring}')
    if stderr:
        raise RuntimeError(f'[ERROR][ansible.py] Running playbook {path} with {tagstring} {varstring} raised:\n{stderr}')
    else:
        return stdout


## Functions for specific plays

# def copy(host, path):
#     tags = ['copy-file']

#     pathArr = path.split('/')
#     basepath = '/'.join(pathArr[:-1])
#     filename = pathArr[-1]
#     vars = {
#         "dir": basepath,
#         "filename": filename
#     }

#     return playbook('/etc/ansible/utils.yml', tags, vars)
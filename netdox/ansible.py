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

def icinga_set_host(address, location=None, icinga=None, template="generic-host", display_name=None):
    """
    Adds host to a specified Icinga if it does not already exist
    """
    icinga = icinga_setloc(location, icinga)
    if icinga:
        tags = ['set-host']
        vars = {
            "icinga": icinga,
            "host": address,
            "template": template
            }
        if display_name:
            vars['display_name'] = display_name
        else:
            vars['display_name'] = address
        
        print(f'[INFO][ansible.py] Set {template} for {address} in {icinga}')
        stdout = playbook('/etc/ansible/icinga.yml', tags, vars)
        if 'failed=0' not in stdout:
            raise RuntimeError(f'[ERROR][ansible.py] One or more tasks failed during set-host with template {template} for address {address} on {icinga}. Printout:\n{stdout}')
    else:
        return None


def icinga_pause(address, location=None, icinga=None):
    """
    Pauses the monitoring of the host object with a given address
    """
    icinga = icinga_setloc(location, icinga)
    if icinga:     
        tags = ['pause-host']
        vars = {
            "icinga": icinga,
            "host": address
            }
        
        stdout = playbook('/etc/ansible/icinga.yml', tags, vars)
        if 'failed=0' not in stdout:
            raise RuntimeError(f'[ERROR][ansible.py] One or more tasks failed during pause-host for address {address} on {icinga}. Printout:\n{stdout}')
        else:
            return stdout
    else:
        return None

def icinga_unpause(address, location=None, icinga=None):
    """
    Unpauses the monitoring of the host object with a given address
    """
    icinga = icinga_setloc(location, icinga)
    if icinga:
        tags = ['unpause-host']
        vars = {
            "icinga": icinga,
            "host": address,
            }

        stdout = playbook('/etc/ansible/icinga.yml', tags, vars)
        if 'failed=0' not in stdout:
            raise RuntimeError(f'[ERROR][ansible.py] One or more tasks failed during unpause-host for address {address} on {icinga}. Printout:\n{stdout}')
        else:
            return stdout
    else:
        return None
    
def icinga_setloc(location, icinga):
    if not location and not icinga:
        raise ValueError('[ERROR][ansible.py] Either location or icinga must be defined.')
    elif location and not icinga:
        for host in icinga_hosts:
            if location in icinga_hosts[host]['locations']:
                icinga = host
        if not icinga:
            if location not in utils._location_map:
                raise ValueError(f'[ERROR][ansible.py] Unrecognised location {location}')
            else:
                print(f'[WARNING][ansible.py] No Icinga defined for location {location}')
                return None
    return icinga


def copy(host, path):
    tags = ['copy-file']

    pathArr = path.split('/')
    basepath = '/'.join(pathArr[:-1])
    filename = pathArr[-1]
    vars = {
        "dir": basepath,
        "filename": filename
    }

    return playbook('/etc/ansible/utils.yml', tags, vars)
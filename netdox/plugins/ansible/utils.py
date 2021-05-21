from typing import Tuple
from paramiko import client, AutoAddPolicy
import json, re

## Main functions

def exec(cmd: str) -> Tuple[str, str]:
    """
    Executes a command on the ansible machine
    """
    sshclient = client.SSHClient()
    sshclient.set_missing_host_key_policy(AutoAddPolicy())
    sshclient.connect('ansiblesy4.allette.com.au', username='root', key_filename='plugins/ansible/src/ssh/ssh-privatekey')
    stdin, stdout, stderr = sshclient.exec_command(cmd)
    stdin.close()
    stdout = str(stdout.read(), encoding='utf-8')
    stderr = str(stderr.read(), encoding='utf-8')
    return (stdout, stderr)

def playbook(path: str, tags: list[str]=[], vars: dict[str, str]={}) -> str:
    """
    Runs a playbook with optional tags and extra vars
    """
    # encode dict as extra vars
    varstring = ''
    for key, value in vars.items():
        if not varstring:
            varstring = '-e "'
        else:
            varstring += ' '
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
    errors = validateStdout(stdout)
    if stderr:
        raise RuntimeError(f'[ERROR][ansible.py] Running playbook {path} with {tagstring} {varstring} failed:\n{stderr}')
    elif errors:
        raise RuntimeError(f'[ERROR][ansible.py] One or more tasks failed running playbook {path} with {tagstring} {varstring}:\n{json.dumps(errors, indent=1)}')
    else:
        return stdout

failed_task_pattern = re.compile(r'FAILED! => (?P<json>{.+?})\s*\n')
def validateStdout(stdout: str) -> list[dict]:
    stderrs = []
    failed = re.finditer(failed_task_pattern, stdout)
    for task in failed:
        jsondata = json.loads(task['json'])
        stderrs.append(jsondata['stderr'])
    return stderrs
import json
import re

import ssh

import utils


def playbook(path: str, tags: list[str]=[], vars: dict[str, str]={}) -> str:
    """
    Runs a playbook with optional tags and extra vars

    :param path: The path to the playbook to run
    :type path: str
    :param tags: A list of tags to pass to this ansible command, defaults to []
    :type tags: list[str], optional
    :param vars: A dictionary of key/value pairs to pass to this ansible command, defaults to {}
    :type vars: dict[str, str], optional
    :raises RuntimeError: If the cmd printed anything to stderr or one of the playbook tasks failed.
    :return: The text printed to stdout by *cmd*.
    :rtype: str
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

    stdout, stderr = ssh.exec(f'ansible-playbook {path} {tagstring} {varstring}', utils.config()['ansible']['host'])
    errors = validateStdout(stdout)
    if stderr:
        raise RuntimeError(f'[ERROR][ansible.py] Running playbook {path} with {tagstring} {varstring} failed:\n{stderr}')
    elif errors:
        raise RuntimeError(f'[ERROR][ansible.py] One or more tasks failed running playbook {path} with {tagstring} {varstring}:\n{json.dumps(errors, indent=1)}')
    else:
        return stdout

failed_task_pattern = re.compile(r'FAILED! => (?P<json>{.+?})\s*\n')
def validateStdout(string: str) -> list[dict]:
    """
    Returns a list of strings matching the ansible *failed task* pattern.

    :param string: The string to search.
    :type string: str
    :return: A list of strings matching the pattern.
    :rtype: list[dict]
    """
    stderrs = []
    failed = re.finditer(failed_task_pattern, string)
    for task in failed:
        jsondata = json.loads(task['json'])
        stderrs.append(jsondata['stderr'])
    return stderrs

from typing import Union
from paramiko import client, AutoAddPolicy

def exec(cmd: str, host: str, port: int = 22, username: str = 'root', private_key: str = 'src/ssh/ssh-ed25519') -> str:
    """
    Executes a single command on the host machine through SSH.

    :Args:
        cmd:
            The command to execute on the remote machine
        host:
            The remote machine to execute the command on
        port:
            The port to use for the SSH connection
        username:
            The username to login with when starting the SSH session
        private_key:
            Path of the private key to use for authentication

    :Returns:
        The string(s) printed to stdout by this operation
    """
    sshclient = client.SSHClient()
    sshclient.set_missing_host_key_policy(AutoAddPolicy())
    sshclient.connect(host, port = port, username = username, key_filename = private_key)
    stdin, stdout, stderr = sshclient.exec_command(cmd)
    stdin.close()
    stdout = str(stdout.read(), encoding='utf-8')
    stderr = str(stderr.read(), encoding='utf-8')
    sshclient.close()
    if stderr:
        raise RuntimeError(f'Command "{cmd}" failed over SSH on {host}: \n{stderr}')
    else:
        return stdout

def exec_batch(cmdlist: list[str], host: str, port: int = 22, username: str = 'root',
                private_key: str = 'src/ssh/ssh-ed25519', error_action: str = 'continue') -> list[Union[str, RuntimeError]]:
    """
    Executes a single command on the host machine through SSH.

    :Args:
        cmd:
            The command to execute on the remote machine
        host:
            The remote machine to execute the command on
        port:
            The port to use for the SSH connection
        username:
            The username to login with when starting the SSH session
        private_key:
            Path of the private key to use for authentication
        error_action:
            One of: continue, halt. If halt, a RuntimeError exception will be raised in the event that one of the commands in
            cmdlist raises an error on the remote machine (same as exec). If continue, the exception object will be appended to the list of
            return values instead, and the text content will be the content of *stderr* only.

    :Returns:
        The string(s) printed to stdout by this operation
    """

    returnVals = []
    sshclient = client.SSHClient()
    sshclient.set_missing_host_key_policy(AutoAddPolicy())
    sshclient.connect(host, port = port, username = username, key_filename = private_key)
    for cmd in cmdlist:
        stdin, stdout, stderr = sshclient.exec_command(cmd)
        stdin.close()
        stdout = str(stdout.read(), encoding='utf-8')
        stderr = str(stderr.read(), encoding='utf-8')
        if stderr:
            if error_action == 'continue':
                returnVals.append(RuntimeError(stderr))
            else:
                raise RuntimeError(f'Command "{cmd}" failed over SSH on {host}: \n{stderr}')
        else:
            returnVals.append(stdout)
    sshclient.close()

    return returnVals

from paramiko import client, AutoAddPolicy
from textwrap import dedent
from functools import wraps
from typing import Tuple
import utils

icinga_hosts = utils.auth()['plugins']['icinga']

###################################
# Abstract Functions / Decorators #
###################################

def exec(cmd: str, host: str) -> Tuple[str, str]:
    """
    Executes a command on the host machine through SSH.
    """
    sshclient = client.SSHClient()
    sshclient.set_missing_host_key_policy(AutoAddPolicy())
    sshclient.connect(host, username='root', key_filename='src/ssh/ssh-ed25519')
    stdin, stdout, stderr = sshclient.exec_command(cmd)
    stdin.close()
    stdout = str(stdout.read(), encoding='utf-8')
    stderr = str(stderr.read(), encoding='utf-8')
    if stderr:
        raise RuntimeError(f'Command "{cmd}" failed over SSH on {host}: \n{stderr}')
    else:
        return stdout

def setloc(func):
    """
    This decorator contains the location handling functionality from set_host / rm_host, 
    stored here to make the functions smaller and their purpose clearer.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        args = list(args)
        if 'icinga' in kwargs:
            pass

        elif 'location' in kwargs:
            for icinga, conf in icinga_hosts.items():
                if kwargs['location'] in conf['locations']:
                    kwargs['icinga'] = icinga
                del kwargs['location']

        elif len(args) > 1:
            tmp = []
            for arg in args[1:3]:
                if arg in icinga_hosts:
                    host = arg
                    tmp.append(arg)
                else:
                    for icinga, conf in icinga_hosts.items():
                        if arg in conf['locations']:
                            host = icinga
                            tmp.append(arg)
            for arg in tmp:
                args.remove(arg)

        if not host:
            if 'location' in kwargs:
                raise ValueError(f'Unrecognised location {kwargs["location"]}')
            elif 'icinga' in kwargs:
                raise ValueError(f'Unrecognised Icinga {kwargs["icinga"]}')
            else:
                raise ValueError(f'Missing kwargs; Must provide one of icinga, location.')
        else:
            kwargs['icinga'] = host
            return func(*args, **kwargs)
    return wrapper


####################
# Command Builders #
####################

@setloc
def set_host(address: str, icinga: str = '', location: str = '', template: str = 'generic-host', display_name: str = '') -> str:
    """
    Creates a file on an Icinga host containing a host object definition with the given template and the given address.
    """
    if not display_name: display_name = address

    cmd = dedent(f"""
    /bin/echo \\
    'object Host "{display_name}" {{
        import "{template}"
        address = "{address}"
        vars.group = "generated"
    }}' > /etc/icinga2/conf.d/hosts/generated/{address.replace('.','_')}.conf && icinga2 daemon -C && systemctl reload icinga2
    """)

    return exec(cmd, host=icinga)

@setloc
def rm_host(address: str, icinga: str = '', location: str = '') -> str:
    """
    Removes the generated monitor for a host with a specified address.
    """
    cmd = f'rm -f /etc/icinga2/conf.d/hosts/generated/{address.replace(".","_")}.conf'

    return exec(cmd, host=icinga)
"""
SSH Functions
*************

Provides functions for executing commands on Icinga instances over SSH,
and some convenience functions for creating/deleting generated monitors etc.
"""
import logging
from functools import wraps
from textwrap import dedent

from netdox import utils
from paramiko import AutoAddPolicy, client

logger = logging.getLogger(__name__)

def exec(cmd: str, host: str, port: int = 22, username: str = 'root', private_key: str = None) -> str:
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


def setloc(func):
    """
    This decorator contains the location handling functionality from set_host / rm_host, 
    stored here to make the functions smaller and their purpose clearer.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        host: str = ''

        if 'icinga' in kwargs:
            host = kwargs['icinga']

        elif 'location' in kwargs:
            for icinga, conf in utils.config('icinga').items():
                if kwargs['location'] in conf['locations']:
                    host = icinga

        if not host:
            if 'location' in kwargs:
                raise ValueError(f'Unrecognised location {kwargs["location"]}')
            elif 'icinga' in kwargs:
                raise ValueError(f'Unrecognised Icinga {kwargs["icinga"]}')
            else:
                raise ValueError(f'Missing kwargs; Must provide a valid value for one of: icinga, location.')
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

    :param address: The address to use for the host object in Icinga.
    :type address: str
    :param icinga: The domain name of the Icinga instance to create the object in. Required if *location* is not set.
    :type icinga: str
    :param location: The location of the Icinga instance to use, as it appears in ``locations.json``. Required if *icinga* is not set.
    :type location: str
    :param template: The template name to use for the host object
    :type template: str
    :param display_name: The display name to use for the object. Defaults to *address*.
    :type display_name: str
    """
    if not display_name: display_name = address

    cmd = dedent(f"""
    /bin/echo \\
    'object Host "{display_name}" {{
        import "{template}"
        address = "{address}"
        vars.group = "generated"
    }}' > /etc/icinga2/conf.d/hosts/generated/{address.replace('.','_')}.conf
    """)

    logger.info(f'Setting template for {address} to {template} in {icinga}')
    return exec(cmd, host=icinga)

@setloc
def rm_host(address: str, icinga: str = '', location: str = '') -> str:
    """
    Deletes the file on an Icinga host containing the host object definition with the given address.

    :param address: The address of the host object to delete.
    :type address: str
    :param icinga: The domain name of the Icinga instance to look for the object in. Required if *location* is not set.
    :type icinga: str
    :param location: The location of the Icinga instance to use, as it appears in ``locations.json``. Required if *icinga* is not set.
    :type location: str
    """
    cmd = f'rm -f /etc/icinga2/conf.d/hosts/generated/{address.replace(".","_")}.conf'

    logger.info(f'Removing monitor on {address} from {icinga}')
    return exec(cmd, host=icinga)

@setloc
def reload(icinga: str = '', location: str = '') -> str:
    """
    Validates config files and reloads the Icinga2 systemd service.

    :param icinga: The domain name of the Icinga instance to look for the object in. Required if *location* is not set.
    :type icinga: str
    :param location: The location of the Icinga instance to use, as it appears in ``locations.json``. Required if *icinga* is not set.
    :type location: str
    """
    cmd = f'icinga2 daemon -C && systemctl reload icinga2'

    logger.info(f'Reloading Icinga2 service on {icinga}')
    return exec(cmd, host=icinga)

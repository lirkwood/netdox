"""
SSH Functions
*************

Provides functions for executing commands on Icinga instances over SSH,
and some convenience functions for creating/deleting generated monitors etc.
"""
from plugins.ssh import exec
from textwrap import dedent
from functools import wraps
import utils

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
            for icinga, conf in utils.config()['plugins']['icinga'].items():
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

    :Args:
        address:
            The address to use for the monitor
        icinga:
            The fqdn of an Icinga instance to create this monitor in (if not present *location* is required)
        location:
            The location of the Icinga instance to use, if there is one configured (if not present *icinga* is required)
        template:
            The template to use for the monitor
        display_name:
            The display name to give the monitor

    :Returns:
        The string(s) printed to stdout by this operation
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

    print(f'[INFO][icinga] Setting template for {address} to {template}')
    return exec(cmd, host=icinga)

@setloc
def rm_host(address: str, icinga: str = '', location: str = '') -> str:
    """
    Deletes the file on an Icinga host containing the host object definition with the given address.

    :Args:
        address:
            The address to look for
        icinga:
            The fqdn of an Icinga instance to create this monitor in (if not present *location* is required)
        location:
            The location of the Icinga instance to use, if there is one configured (if not present *icinga* is required)

    :Returns:
        The string(s) printed to stdout by this operation
    """
    cmd = f'rm -f /etc/icinga2/conf.d/hosts/generated/{address.replace(".","_")}.conf'

    print(f'[INFO][icinga] Removing monitor on {address}')
    return exec(cmd, host=icinga)

@setloc
def reload(icinga: str = '', location: str = '') -> str:
    """
    Validates config files and reloads the Icinga2 systemd service.

    :Args:
        icinga:
            The fqdn of an Icinga instance to create this monitor in (if not present *location* is required)
        location:
            The location of the Icinga instance to use, if there is one configured (if not present *icinga* is required)
    """
    cmd = f'icinga2 daemon -C && systemctl reload icinga2'

    print(f'[INFO][icinga] Reloading Icinga2 service on {icinga}')
    return exec(cmd, host=icinga)
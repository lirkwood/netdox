from plugins.ansible.utils import *
import utils

icinga_hosts = utils.auth['plugins']['icinga']

def set_host(address, location=None, icinga=None, template="generic-host", display_name=None):
    """
    Adds host to a specified Icinga if it does not already exist
    """
    icinga = setloc(location, icinga)
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


def pause(address, location=None, icinga=None):
    """
    Pauses the monitoring of the host object with a given address
    """
    icinga = setloc(location, icinga)
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

def unpause(address, location=None, icinga=None):
    """
    Unpauses the monitoring of the host object with a given address
    """
    icinga = setloc(location, icinga)
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
    
def setloc(location, icinga):
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
"""
This plugin is used to both inject monitoring information into DNS record documents,
and modify the monitors based on values configured in PageSeeder.

The 'icinga_template' attribute, if configured on an applied label, will provide the desired monitor template name for a domain.
If there is a manually specified monitor on an address, no modifications will be made and any generated monitors will be removed.
"""
from netdox.plugins.icinga.api import TEMPLATE_ATTR
from netdox.plugins.icinga.manager import MonitorManager

def footers(network):
    """
    Adds Icinga monitor information to the Domains in the network.
    If the monitor template does not match the configured value, it will be updated.
    If the monitor continues to appear invalid after 3 attempts it will be abandoned.
    This function will also remove any Netdox-generated monitors on domains which are 
    not present in the network.

    :param network: The network.
    :type network: Network
    """
    mgr = MonitorManager(network)
    mgr.validateNetwork()
    mgr.addPSMLFooters()

__stages__ = {'footers': footers}

__attrs__ = {TEMPLATE_ATTR}

__config__ = {
    "hostname": {
        "locations": [''],
        "username": '',
        "password": ''
    }
}
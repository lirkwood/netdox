"""
This plugin is used to both inject monitoring information into DNS record documents,
and modify the monitors based on values configured in PageSeeder.

The 'icinga_template' attribute, if configured on an applied label, will provide the desired monitor template name for a domain.
If there is a manually specified monitor on an address, no modifications will be made and any generated monitors will be removed.
"""
from netdox.plugins.icinga.api import runner, TEMPLATE_ATTR

__stages__ = {'footers': runner}

__attrs__ = {TEMPLATE_ATTR}
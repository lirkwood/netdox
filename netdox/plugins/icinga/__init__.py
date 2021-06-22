"""
This plugin is used to both inject monitoring information into DNS record documents,
and modify the monitors based on values configured in PageSeeder.

The 'template' property, if present in a DNS role, will provide the desired monitor template for a domain.
If there is a manually specified monitor on an address, no modifications will be made and any generated monitors will be removed.
"""
stage = 'post-write'

from plugins.icinga.api import runner
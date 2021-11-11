"""
Webhook Actions
***************

Provides some functions which parse and act upon the impulse sent by a PageSeeder webhook.

Can be used to create a XenOrchestra VM.
"""

from typing import Optional
from netdox import utils
from netdox.plugins.xenorchestra.objs import XOServer


@utils.handle
async def createVM(uuid: str, name: str = None) -> Optional[dict]:
    """
    Given the UUID of some VM-like object, creates a clone VM

    :param uuid: The UUID of the object to clone.
    :type uuid: str
    :param name: The name to give the new object, defaults to None
    :type name: bool, optional
    :raises ValueError: If the object with the specified UUID is not a valid VM template.
    """
    async with XOServer(**utils.config('xenorchestra')) as xo:
        info = await xo.fetchObjs({'uuid': uuid})

        object = info[list(info)[0]]
        name = name or f"{object['name_label']} CLONE"
        # if given
        if object['type'] == 'VM' or object['type'] == 'VM-snapshot':
            return await xo.call('vm.clone', {
                'id': uuid,
                'name': name,
                'full_copy': True
            })

        elif object['type'] == 'VM-template':
            return await xo.call('vm.create', {
                'bootAfterCreate': True,
                'template': uuid,
                'name_label': name
            })

        else:
            raise ValueError(f'Invalid template type {object["type"]}')

"""
Webhook Actions
***************

Provides some functions which parse and act upon the impulse sent by a PageSeeder webhook.

Can be used to create a XenOrchestra VM.
"""

from plugins.xenorchestra import call, authenticate
from plugins.xenorchestra.fetch import fetchObj
import utils

@utils.handle
@authenticate
async def createVM(uuid: str, name: bool = None):
    """
    Given the UUID of some VM-like object, creates a clone VM

    :Args:
        uuid:
            The UUID of an object which can be cloned or used as a VM template
        name:
            (Optional) The name to give the new VM
    """
    info = await fetchObj(uuid)
    if len(info.keys()) > 1:
        raise ValueError(f'Ambiguous UUID {uuid}')
    else:

        object = info[list(info)[0]]
        if not name:
            name = f"{object['name_label']} CLONE"
        # if given
        if object['type'] == 'VM' or object['type'] == 'VM-snapshot':
            return await call('vm.clone', {
                'id': uuid,
                'name': name,
                'full_copy': True
            })

        elif object['type'] == 'VM-template':
            return await call('vm.create', {
                'bootAfterCreate': True,
                'template': uuid,
                'name_label': name
            })

        else:
            raise ValueError(f'Invalid template type {object["type"]}')
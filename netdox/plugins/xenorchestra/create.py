"""
Webhook Actions
***************

Provides some functions which parse and act upon the impulse sent by a PageSeeder webhook.

Can be used to create a XenOrchestra VM.
"""

from netdox import utils
from netdox.plugins.xenorchestra import authenticate, call
from netdox.plugins.xenorchestra.fetch import fetchObj


@utils.handle
@authenticate
async def createVM(uuid: str, name: bool = None) -> None:
    """
    Given the UUID of some VM-like object, creates a clone VM

    :param uuid: The UUID of the object to clone.
    :type uuid: str
    :param name: The name to give the new object, defaults to None
    :type name: bool, optional
    :raises ValueError: If the object with the specified UUID is not a valid VM template.
    """
    info = await fetchObj(uuid)

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

from plugins.xenorchestra import call, authenticate
from plugins.xenorchestra.fetch import fetchObj
import utils

@utils.handle
@authenticate
async def createVM(uuid, name=None):
    """
    Given the UUID of some VM-like object, creates a clone VM
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
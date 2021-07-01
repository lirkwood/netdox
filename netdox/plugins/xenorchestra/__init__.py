"""
Used to read and modify the VMs managed by Xen Orchestra
"""
from textwrap import dedent
from functools import wraps
import os, json, random, websockets
import utils
stage = 'nodes'

def init():
    """
    Some initialisation for the plugin to work correctly

    :meta private:
    """
    global creds
    creds = utils.auth()['plugins']['xenorchestra']
    global url
    url = f"wss://{creds['host']}/api/"
    if not os.path.exists('plugins/xenorchestra/src'):
        os.mkdir('plugins/xenorchestra/src')

    for type in ('vms', 'hosts', 'pools', 'templates'):
        with open(f'plugins/xenorchestra/src/{type}.xml','w') as stream:
            stream.write(dedent(f"""
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE {type} [
            <!ENTITY json SYSTEM "{type}.json">
            ]>
            <{type}>&json;</{type}>""").strip())


##################################
# Generic websocket interactions #
##################################

async def call(method: str, params: dict = {}, notification: bool = False) -> dict:
    """
    Makes a call with some given method and params, returns a JSON object

    :Args:
        method:
            The RPC method to call
        params:
            A dictionary of parameters to call the method with
        notification:
            If true no response is expected and no ID is sent

    :Returns:
        The JSON returned by the server
    """
    if notification:
        await websocket.send(json.dumps({
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }))
    else:
        id = f"netdox-{random.randint(0, 99)}"
        await websocket.send(json.dumps({
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": id
        }))
        return await reciever(id)


def authenticate(func):
    """
    Decorator used to establish a WSS connection before the function runs
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        global websocket
        async with websockets.connect(url, max_size=3000000) as websocket:
            if 'error' in await call('session.signInWithPassword', {'email': creds['username'], 'password': creds['password']}):
                raise RuntimeError(f'Failed to sign in with user {creds["username"]}')
            else:
                return await func(*args, **kwargs)
    return wrapper


global frames
frames = {}
async def reciever(id: int) -> dict:
    """
    Consumes responses sent by websocket server, returns the one with the specified ID.

    :Args:
        id:
            The ID generated alongside the outgoing message which identifies the response message
    
    :Returns:
        The JSON returned by the server
    """
    if id in frames:
        return frames[id]
    async for message in websocket:
        message = json.loads(message)
        if 'id'in message:
            if message['id'] == id:
                return message
            else:
                frames[message['id']] = message


from plugins.xenorchestra.fetch import runner
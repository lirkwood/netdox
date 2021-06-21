from textwrap import dedent
import os, json, random, websockets
import utils
stage = 'resource'

def init():
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

async def call(method, params={}, notification=False):
    """
    Makes a call with some given method and params, returns a JSON object
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
async def reciever(id):
    """
    Consumes responses sent by websocket server, returns the one with the specified ID.
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
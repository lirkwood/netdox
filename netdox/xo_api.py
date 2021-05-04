import websockets, asyncio, random, json, re
import iptools, utils

with open('src/authentication.json', 'r') as stream:
    creds = json.load(stream)['xenorchestra']
global url
url = f"wss://{creds['host']}/api/"

def build_jsonrpc(method, params={}, notification=False):
    """
    Constructs a JSONRPC query based on some method and its params
    """
    if notification:
        return json.dumps({
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        })
    else:
        id = f"netdox-{random.randint(0, 99)}"
        return json.dumps({
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": id
        }), id

def authenticate(func):
    """
    Decorator used to call session.singInWithPassword and establish a websocket before doing some operation.
    """
    async def wrapper(*args, **kwargs):
        async with websockets.connect(url, max_size=3000000) as websocket:
            print('auth start')
            request, id = build_jsonrpc('session.signInWithPassword', {'email': creds['username'], 'password': creds['password']})
            await websocket.send(request)
            print('sent')
            resp = json.loads(await websocket.recv())
            if 'error' in resp:
                raise RuntimeError(f'[ERROR][xo_api.py] Failed to sign in with user {creds["username"]}')
            else:
                return await func(*args, **kwargs, websocket=websocket)
    return wrapper

global frames
frames = {}
async def reciever(id, websocket):
    if id in frames:
        return frames[id]
    async for message in websocket:
        message = json.loads(message)
        if 'id' not in message:
            pass
        elif message['id'] == id:
            return message
        else:
            frames[message['id']] = message


@utils.critical
@authenticate
async def fetchObjects(dns, websocket):
    controllers = set()
    poolHosts = {}
    pools = fetchType('pool', websocket)
    hosts = fetchType('host', websocket)
    vms = fetchType('VM', websocket)
    pools = await pools
    for poolId in pools:
        pool = pools[poolId]
        poolHosts[poolId] = []
        controllers.add(pool['master'])
    writeJson(pools, 'pools')

    for hostId in (await hosts):
        host = hosts[hostId]
        if hostId not in controllers:
            poolHosts[host['$pool']].append(hostId)
            host['subnet'] = iptools.sort(host['address'])
    writeJson(hosts, 'hosts')

    hostVMs = {}
    for vmId in (await vms):
        vm = vms[vmId]
        vm['name_label'] = re.sub(r'[/\\]','', vm['name_label'])
        
        if vm['$container'] not in hostVMs:
            hostVMs[vm['$container']] = []
        hostVMs[vm['$container']].append(vm['uuid'])
        try:
            vm['subnet'] = iptools.sort(vm['mainIpAddress'])
        except Exception:
            pass

        vm['domains'] = []
        if 'mainIpAddress' in vm:
            for domain in dns:
                if vm['mainIpAddress'] in dns[domain].ips:
                    vm['domains'].append(domain)
        else:
            if vm['power_state'] == 'Running':
                print(f'[WARNING][xo_api.py] VM {vm["name_label"]} has no IP address')
    writeJson(vms, 'vms')
    writeJson(poolHosts, 'devices')
    writeJson(hostVMs, 'residents')
            

async def fetchType(type, websocket):
    request, id = build_jsonrpc('xo.getAllObjects', {
    'filter': {
        'type': type
    }})
    await websocket.send(request)
    resp = await reciever(id, websocket)
    try:
        return resp['result']
    except KeyError:
        raise KeyError('caught')
    

def writeJson(data, type):
    with open(f'src/{type}.json', 'w') as stream:
        stream.write(json.dumps(data, indent=2))
    del data


@utils.handle
@authenticate
async def createVM(template, name, websocket):
    request = build_jsonrpc('xo.getAllObjects', {
    'filter': {
        'uuid': template
    }})
    await websocket.send(request)
    info = json.loads(await websocket.recv())['result']
    if len(info.keys()) > 1:
        raise ValueError(f'[ERROR][xo_api.py] Ambiguous UUID {template}')
    else:

        object = info[list(info)[0]]
        if object['type'] == 'VM' or object['type'] == 'VM-snapshot':
            request = build_jsonrpc('vm.clone', {
                'id': template,
                'name': name,
                'full_copy': True
            })
        elif object['type'] == 'VM-template':
            request = build_jsonrpc('vm.create', {
                'bootAfterCreate': True,
                'template': template,
                'name_label': name
            })
        else:
            raise ValueError(f'[ERROR][xo_api.py] Invalid template type {object["type"]}')

        await websocket.send(request)
        resp = json.loads(await websocket.recv())
        return resp
import websockets, asyncio, json, re
import iptools, utils

## Utility functions

with open('src/authentication.json', 'r') as stream:
    creds = json.load(stream)['xenorchestra']
global url
url = f"wss://{creds['host']}/api/"

def build_jsonrpc(method, params={}):
    """
    Constructs a JSONRPC query based on some method and its params
    """
    return json.dumps({
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    })

def signFirst(func):
    """
    Decorator used to call session.singInWithPassword and establish a websocket before doing some operation.
    """
    async def wrapper(*args, **kwargs):
        global websocket
        async with websockets.connect(url) as websocket:
            request = build_jsonrpc('session.signInWithPassword', {'email': creds['username'], 'password': creds['password']})
            await websocket.send(request)
            resp = json.loads(await websocket.recv())
            if 'error' in resp:
                raise RuntimeError(f'[ERROR][xo_api.py] Failed to sign in with user {creds["username"]}')
            else:
                return await func(*args, **kwargs)
    return wrapper

@utils.critical
@signFirst
async def fetchObjects(dns):
    controllers = set()
    poolHosts = {}
    pools = fetchType('pool')
    hosts = fetchType('host')
    vms = fetchType('VM')
    for poolId in (await pools):
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
            
async def fetchType(type):
    global websocket
    request = build_jsonrpc('xo.getAllObjects', {
    'filter': {
        'type': type
    }})
    await websocket.send(request)
    resp = json.loads(await websocket.recv())
    print(resp)
    return resp['result']
    
def writeJson(data, type):
    with open(f'src/{type}.json', 'w') as stream:
        stream.write(json.dumps(data, indent=2))
    del data


@utils.handle
@signFirst
async def createVM(template, name):
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

if __name__ == '__main__':
    asyncio.run(createVM('01a5ca9f-6fbd-afac-4c59-a506bb1dcb85','api test'))
import websockets, asyncio, json, re
import iptools, utils

## Utility functions

with open('src/authentication.json', 'r') as stream:
    creds = json.load(stream)['xenorchestra']
global url
url = f"wss://{creds['host']}/api/"

def build_jsonrpc(method, params={}):
    return json.dumps({
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    })

async def signFirst(func):
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
    return await wrapper


@signFirst
async def fetchObjects(dns):
    controllers = set()
    poolHosts = {}
    pools = fetchType('pool')
    for pool in pools:
        poolHosts[pool['uuid']] = []
        controllers.add(pool['master'])
    writeJson(pools, 'pools')

    hosts = fetchType('host')
    for host in hosts:
        if host['uuid'] not in controllers:
            poolHosts[host['$pool']].append(host['uuid'])
            host['subnet'] = iptools.sort(host['address'])
    writeJson(hosts, 'hosts')

    hostVMs = {}
    vms = fetchType('VM')
    for vm in vms:
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
    request = build_jsonrpc(f'xo.getAllObjects', {
    'filter': {
        'type': type
    }})
    await websocket.send(request)
    return json.loads(await websocket.recv())
    
def writeJson(data, type):
    with open(f'src/{type}.json', 'w') as stream:
        stream.write(json.dumps(data, indent=2))
    del data
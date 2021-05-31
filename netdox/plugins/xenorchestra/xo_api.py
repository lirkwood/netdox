from requests.api import request
import websockets, asyncio, random, json, re
import iptools, utils

## Some initialisation

creds = utils.auth()['plugins']['xenorchestra']
global url
url = f"wss://{creds['host']}/api/"

def writeJson(data, name):
    """
    Writes some data to a json file and then deletes it from memory
    """
    with open(f'plugins/xenorchestra/src/{name}.json', 'w') as stream:
        stream.write(json.dumps(data, indent=2))
    del data

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
                raise RuntimeError(f'[ERROR][xo_api.py] Failed to sign in with user {creds["username"]}')
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
        if 'id' not in message:
            pass
        elif message['id'] == id:
            return message
        else:
            frames[message['id']] = message


#########################
# Convenience functions #
#########################

async def fetchType(type: str):
    """
    Fetches all objects of a given type
    """
    return (await call('xo.getAllObjects', {
    'filter': {
        'type': type
    }}))['result']
    
    
async def fetchObj(uuid: str):
    """
    Fetches an object by UUID
    """
    return (await call('xo.getAllObjects', {
    'filter': {
        'uuid': uuid
    }}))['result']


async def fetchObjByFields(fieldmap: dict[str, str]):
    return (await call('xo.getAllObjects', {
    'filter': fieldmap}))['result']

##################
# User functions #
##################

def runner(forward_dns: dict[str, utils.DNSRecord], reverse_dns: dict[str, utils.DNSRecord]):
    # Generate XO Docs
    vms, pools, hosts = asyncio.run(fetchObjects(forward_dns))
    del pools, hosts
    utils.xslt('plugins/xenorchestra/vms.xsl', 'plugins/xenorchestra/src/vms.xml')
    utils.xslt('plugins/xenorchestra/hosts.xsl', 'plugins/xenorchestra/src/hosts.xml')
    utils.xslt('plugins/xenorchestra/pools.xsl', 'plugins/xenorchestra/src/pools.xml')

    # Generate template map for webhooks
    asyncio.run(template_map(vms))

    # Link domains to vms
    for domain in forward_dns:
        dns = forward_dns[domain]
        for uuid in vms:
            vm = vms[uuid]
            try:
                if vm['mainIpAddress'] in dns.ips:
                    dns.link(uuid, 'vm')
            except KeyError:
                pass

@authenticate
async def fetchObjects(dns):
    """
    Fetches info about pools, hosts, and VMs
    """
    controllers = set()
    poolHosts = {}
    pools = await fetchType('pool')
    hosts = await fetchType('host')
    vms = await fetchType('VM')
    
    for poolId in pools:
        pool = pools[poolId]
        poolHosts[poolId] = []
        controllers.add(pool['master'])
    writeJson(pools, 'pools')

    for hostId in hosts:
        host = hosts[hostId]
        if hostId not in controllers:
            poolHosts[host['$pool']].append(hostId)
            host['subnet'] = iptools.sort(host['address'])
    writeJson(hosts, 'hosts')

    hostVMs = {}
    for vmId in vms:
        vm = vms[vmId]
        
        if vm['$container'] not in hostVMs:
            hostVMs[vm['$container']] = []
        hostVMs[vm['$container']].append(vm['uuid'])

        vm['domains'] = []
        if 'mainIpAddress' in vm:
            if iptools.valid_ip(vm['mainIpAddress']):
                vm['subnet'] = iptools.sort(vm['mainIpAddress'])
                for domain in dns:
                    if vm['mainIpAddress'] in dns[domain].ips:
                        vm['domains'].append(domain)
            else:
                print(f'[WARNING][xo_api.py] VM {vm["name_label"]} has invalid IPv4 address {vm["mainIpAddress"]}')
                del vm['mainIpAddress']
        else:
            if vm['power_state'] == 'Running':
                print(f'[WARNING][xo_api.py] VM {vm["name_label"]} has no IP address')
    writeJson(vms, 'vms')
    writeJson(poolHosts, 'devices')
    writeJson(hostVMs, 'residents')

    return vms, hosts, pools


@utils.handle
@authenticate
async def createVM(uuid, name=None):
    """
    Given the UUID of some VM-like object, creates a clone VM
    """
    info = await fetchObj(uuid)
    if len(info.keys()) > 1:
        raise ValueError(f'[ERROR][xo_api.py] Ambiguous UUID {uuid}')
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
            raise ValueError(f'[ERROR][xo_api.py] Invalid template type {object["type"]}')


@utils.handle
@authenticate
async def template_map(vms):
    """
    Generates json with all vms/snapshots/templates
    """
    vmSource = {
        'vms': {},
        'snapshots': {},
        'templates': {}
    }
    templates = await fetchType('VM-template')
    snapshots = await fetchType('VM-snapshot')

    for vm in vms:
        if vms[vm]['power_state'] == 'Running':
            name = vms[vm]['name_label']
            vmSource['vms'][name] = vm

    for snapshot in snapshots:
        name = snapshots[snapshot]['name_label']
        vmSource['snapshots'][name] = snapshot
        
    for template in templates:
        name = templates[template]['name_label']
        vmSource['templates'][name] = template

    with open('plugins/xenorchestra/src/templates.json', 'w', encoding='utf-8') as stream:
        stream.write(json.dumps(vmSource, indent=2, ensure_ascii=False))
    utils.xslt('plugins/xenorchestra/templates.xsl', 'plugins/xenorchestra/src/templates.xml', 'out/config/templates.psml')
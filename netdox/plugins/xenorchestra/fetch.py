"""
DNS Refresh
***********

Provides a function which links records to their relevant XenOrchestra VMs and generates some documents about said VMs.

This script is used during the refresh process to link DNS records to the VMs they resolve to, and to trigger the generation of a publication which describes all VMs, their hosts, and their host's pool.
"""
from network import IPv4Address, Network
from plugins.xenorchestra import call, authenticate
import asyncio, json
import iptools, utils

## Some initialisation

def writeJson(data, name):
    """
    Writes some data to a json file and then deletes it from memory
    """
    with open(f'plugins/xenorchestra/src/{name}.json', 'w') as stream:
        stream.write(json.dumps(data, indent=2))
    del data


#########################
# Convenience functions #
#########################

async def fetchType(type: str):
    """
    Fetches all objects of a given type

    :Args:
        type:
            The type of object to filter for
    """
    return (await call('xo.getAllObjects', {
    'filter': {
        'type': type
    }}))['result']
    
    
async def fetchObj(uuid: str):
    """
    Fetches an object by UUID

    :Args:
        uuid:
            The UUID of the object to return
    """
    return (await call('xo.getAllObjects', {
    'filter': {
        'uuid': uuid
    }}))['result']


async def fetchObjByFields(fieldmap: dict[str, str]):
    """
    Returns an object which matches the fieldmap dictionary

    :Args:
        fieldmap:
            A dictionary of fields and the values to filter for
    """
    return (await call('xo.getAllObjects', {
    'filter': fieldmap}))['result']

##################
# User functions #
##################

def runner(network: Network):
    """
    Links DNSRecords to the Kubernetes apps they resolve to, and generates the xo_* documents.

    :Args:
        forward_dns:
            A forward DNS set
        _:
            Any object - not used
    """
    # Generate XO Docs
    vms, _,_ = asyncio.run(fetchObjects(network))
    utils.xslt('plugins/xenorchestra/vms.xsl', 'plugins/xenorchestra/src/vms.xml')
    utils.xslt('plugins/xenorchestra/hosts.xsl', 'plugins/xenorchestra/src/hosts.xml')
    utils.xslt('plugins/xenorchestra/pools.xsl', 'plugins/xenorchestra/src/pools.xml')
    utils.xslt('plugins/xenorchestra/pub.xsl', 'plugins/xenorchestra/src/pools.xml', 'out/xenorchestra_pub.psml')

    # Generate template map for webhooks
    asyncio.run(template_map(vms))

@authenticate
async def fetchObjects(network: Network):
    """
    Fetches info about pools, hosts, and VMs

    :Args:
        network:
            A Network object
    
    :Returns:
        Tuple[0]:
            A dictionary of VMs
        Tuple[1]:
            A dictionary of Hosts
        Tupe[2]:
            A dictionary of host Pools
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
                if vm['mainIpAddress'] not in network.ips:
                    network.add(IPv4Address(vm['mainIpAddress']))
                vm['domains'] = network.ips[vm['mainIpAddress']].domains

            else:
                print(f'[WARNING][xenorchestra] VM {vm["name_label"]} has invalid IPv4 address {vm["mainIpAddress"]}')
                del vm['mainIpAddress']
        else:
            if vm['power_state'] == 'Running':
                print(f'[WARNING][xenorchestra] VM {vm["name_label"]} has no IP address')
    writeJson(vms, 'vms')
    writeJson(poolHosts, 'devices')
    writeJson(hostVMs, 'residents')

    return vms, hosts, pools


@utils.handle
@authenticate
async def template_map(vms):
    """
    Generates a PSML file of all objects that can be used to create a VM with ``createVM``

    :Args:
        vms:
            A dictionary of VMs
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
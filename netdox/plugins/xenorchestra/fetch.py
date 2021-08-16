"""
DNS Refresh
***********

Provides a function which links records to their relevant XenOrchestra VMs and generates some documents about said VMs.

This script is used during the refresh process to link DNS records to the VMs they resolve to, and to trigger the generation of a publication which describes all VMs, their hosts, and their host's pool.
"""
import asyncio
import json

from netdox import iptools, utils
from netdox.networkobjs import IPv4Address, Network
from netdox.plugins.xenorchestra import VirtualMachine, authenticate, call

#########################
# Convenience functions #
#########################

async def fetchType(type: str) -> dict:
    """
    Fetches all objects of a given type

    :param type: The type of object to search for
    :type type: str
    :return: The response sent by the server
    :rtype: dict
    """
    return (await call('xo.getAllObjects', {
    'filter': {
        'type': type
    }}))['result']
    
    
async def fetchObj(uuid: str) -> dict:
    """
    Fetches an object by UUID

    :param uuid: The UUID to search for
    :type uuid: str
    :return: The response sent by the server
    :rtype: dict
    """
    return (await call('xo.getAllObjects', {
    'filter': {
        'uuid': uuid
    }}))['result']


async def fetchObjByFields(fieldmap: dict[str, str]) -> dict:
    """
    Returns an object which matches the fieldmap dictionary

    :param fieldmap: A dictionary of key/value pairs to pass to the request
    :type fieldmap: dict[str, str]
    :return: The response sent by the server
    :rtype: dict
    """
    return (await call('xo.getAllObjects', {
    'filter': fieldmap}))['result']

##################
# User functions #
##################

def runner(network: Network):
    """
    Generates VirtualMachine and Host instances and adds them to the network.

    :param network: The network.
    :type network: Network
    """
    # Generate XO Docs
    vms, hostVMs, poolHosts = asyncio.run(makeNodes(network))

    pubdict = {
        pool: {
            hostip: [
                vmuuid for vmuuid in hostVMs[hostip]
            ]
            for hostip in hostlist 
        } 
        for pool, hostlist in poolHosts.items()
    }
    
    # Generate template map for webhooks
    asyncio.run(template_map(vms))
    
    return pubdict

@authenticate
async def makeNodes(network: Network) -> None:
    """
    Fetches info about pools, hosts, and VMs

    :param network: The network
    :type network: Network
    """
    pools = await fetchType('pool')
    hosts = await fetchType('host')
    vms = await fetchType('VM')
    
    # Pools
    poolNames = {}
    poolHosts = {}
    for uuid, pool in pools.items():
        poolNames[uuid] = pool['name_label']
        poolHosts[pool['name_label']] = []


    # Hosts
    hostVMs = {}
    for host in hosts.values():
        hostVMs[host['uuid']] = []
        poolHosts[poolNames[host['$pool']]].append(host['address'])

    # VMs
    for uuid, vm in vms.items():
        if vm['power_state'] == 'Running':
            if 'mainIpAddress' in vm:
                if iptools.valid_ip(vm['mainIpAddress']):

                    if vm['mainIpAddress'] not in network.ips:
                        IPv4Address(network, vm['mainIpAddress'])

                    hostVMs[vm['$container']].append(vm['uuid'])

                    VirtualMachine(
                        network = network,
                        name = vm['name_label'],
                        desc = vm['name_description'],
                        uuid = uuid,
                        template = vm['other']['base_template_name'] if 'base_template_name' in vm['other'] else '—',
                        os = vm['os_version'],
                        host = hosts[vm['$container']]['address'],
                        pool = poolNames[vm['$pool']],
                        private_ip = vm['mainIpAddress'],
                    )

                else:
                    print(f'[WARNING][xenorchestra] VM {vm["name_label"]} has invalid IPv4 address {vm["mainIpAddress"]}')
            else:
                print(f'[WARNING][xenorchestra] VM {vm["name_label"]} has no IP address')

    return vms, \
        {hosts[hostid]['address']: vmlist for hostid, vmlist in hostVMs.items()}, \
        poolHosts


@utils.handle
@authenticate
async def template_map(vms: dict):
    """
    Generates a PSML file of all objects that can be used to create a VM with ``createVM``

    :param vms: A dictionary of all the VMs, as returned by fetchType
    :type vms: dict
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

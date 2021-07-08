"""
DNS Refresh
***********

Provides a function which links records to their relevant XenOrchestra VMs and generates some documents about said VMs.

This script is used during the refresh process to link DNS records to the VMs they resolve to, and to trigger the generation of a publication which describes all VMs, their hosts, and their host's pool.
"""
from collections import defaultdict
from networkobjs import IPv4Address, Network
from plugins.xenorchestra import Host, call, authenticate, VirtualMachine
import asyncio, json
import iptools, utils


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
    vms, _, poolHosts = asyncio.run(makeNodes(network))

    # Generate template map for webhooks
    asyncio.run(template_map(vms))

    with open('plugins/xenorchestra/src/poolHosts.json', 'w') as stream:
        stream.write(json.dumps({key: poolHosts[key] for key in sorted(poolHosts)}))
    utils.xslt('plugins/xenorchestra/pub.xslt', 'plugins/xenorchestra/src/poolHosts.xml', 'out/xopub.psml')

@authenticate
async def makeNodes(network: Network):
    """
    Fetches info about pools, hosts, and VMs
    """
    pools = await fetchType('pool')
    hosts = await fetchType('host')
    vms = await fetchType('VM')
    
    poolNames = {}
    poolHosts = {}
    controllers = set()
    # Pool controller / devices
    for uuid, pool in pools.items():
        poolNames[uuid] = pool['name_label']
        poolHosts[uuid] = []
        controllers.add(pool['master'])

    # VMs
    hostVMs = defaultdict(list)
    for uuid, vm in vms.items():
        if vm['power_state'] == 'Running':
            if 'mainIpAddress' in vm:
                if iptools.valid_ip(vm['mainIpAddress']):

                    if vm['mainIpAddress'] not in network.ips:
                        network.add(IPv4Address(vm['mainIpAddress']))

                    hostVMs[vm['$container']].append(vm['uuid'])

                    existingNode = f'_nd_node_{vm["mainIpAddress"].replace(".","_")}'
                    network.replace(existingNode, VirtualMachine(
                        name = vm['name_label'],
                        desc = vm['name_description'],
                        uuid = uuid,
                        template = vm['other']['base_template_name'] if 'base_template_name' in vm['other'] else '—',
                        os = vm['os_version'],
                        host = vm['$container'],
                        pool = poolNames[vm['$pool']],
                        private_ip = vm['mainIpAddress'],
                    ))

                else:
                    print(f'[WARNING][xenorchestra] VM {vm["name_label"]} has invalid IPv4 address {vm["mainIpAddress"]}')
            else:
                print(f'[WARNING][xenorchestra] VM {vm["name_label"]} has no IP address')

    # Hosts
    for uuid, host in hosts.items():
        if uuid not in controllers:
            poolHosts[host['$pool']].append(uuid)

        existingNode = f'_nd_node_{host["address"].replace(".","_")}'
        network.replace(existingNode, Host(
            name = host['name_label'],
            desc = host['name_description'],
            uuid = uuid,
            cpus = host['CPUs'],
            bios = host['bios_strings'],
            vms = hostVMs[uuid],
            pool = poolNames[host['$pool']],
            private_ip = host['address'],
            public_ips = None,
            domains = None
        ))

    return vms, hostVMs, {poolNames[k]: v for k, v in poolHosts.items()}


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
    utils.xslt('plugins/xenorchestra/templates.xslt', 'plugins/xenorchestra/src/templates.xml', 'out/config/templates.psml')
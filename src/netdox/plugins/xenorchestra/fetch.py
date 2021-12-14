"""
DNS Refresh
***********

Provides a function which links records to their relevant XenOrchestra VMs and generates some documents about said VMs.

This script is used during the refresh process to link DNS records to the VMs they resolve to, and to trigger the generation of a publication which describes all VMs, their hosts, and their host's pool.
"""
import asyncio
import json
import logging

from netdox import iptools, utils
from netdox import IPv4Address, Network
from netdox.nodes import PlaceholderNode
from netdox.plugins.xenorchestra.objs import XOServer, VirtualMachine

logger = logging.getLogger(__name__)

##################
# User functions #
##################

def runner(network: Network) -> dict[str, dict[str, list[str]]]:
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

async def makeNodes(network: Network) -> tuple[dict, dict[str, list[str]], dict[str, list[str]]]:
    """
    Fetches info about pools, hosts, and VMs

    :param network: The network
    :type network: Network
    """
    # TODO rework this whole module to take advantage of XOServer
    async with XOServer(**utils.config('xenorchestra')) as xo:
        pools = await xo.fetchObjs({'type': 'pool'})
        hosts = await xo.fetchObjs({'type': 'host'})
        vms = await xo.fetchObjs({'type': 'VM'})
        
    # Pools
    poolNames: dict[str, str] = {}
    poolHosts: dict[str, list[str]] = {}
    for uuid, pool in pools.items():
        poolNames[uuid] = pool['name_label']
        poolHosts[pool['name_label']] = []


    # Hosts
    hostVMs: dict[str, list[str]] = {}
    for host in hosts.values():
        hostVMs[host['uuid']] = []
        poolHosts[poolNames[host['$pool']]].append(host['address'])
        PlaceholderNode(network, name = host['name_label'], ips = [host['address']])


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
                        tags = vm['tags']
                    )

                else:
                    logger.warning(f'VM {vm["name_label"]} has invalid IPv4 address {vm["mainIpAddress"]}')
            else:
                logger.warning(f'VM {vm["name_label"]} has no IP address')

    return vms, \
        {hosts[hostid]['address']: vmlist for hostid, vmlist in hostVMs.items()}, \
        poolHosts


@utils.handle
async def template_map(vms: dict):
    """
    Generates a PSML file of all objects that can be used to create a VM with ``createVM``

    :param vms: A dictionary of all the VMs, as returned by fetchType
    :type vms: dict
    """
    vmSource: dict[str, dict[str, str]] = {
        'vms': {},
        'snapshots': {},
        'templates': {}
    }
    async with XOServer(**utils.config('xenorchestra')) as xo:
        templates = await xo.fetchObjs({'type': 'VM-template'})
        snapshots = await xo.fetchObjs({'type': 'VM-snapshot'})

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

    with open(utils.APPDIR+ 'plugins/xenorchestra/src/templates.json', 'w', encoding='utf-8') as stream:
        stream.write(json.dumps(vmSource, indent=2, ensure_ascii=False))

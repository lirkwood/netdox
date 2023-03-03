"""
DNS Refresh
***********

Provides a function which links records to their relevant XenOrchestra VMs and generates some documents about said VMs.

This script is used during the refresh process to link DNS records to the VMs they resolve to, and to trigger the generation of a publication which describes all VMs, their hosts, and their host's pool.
"""
import asyncio
import logging

from netdox import utils
from netdox import Network
from netdox.nodes import DefaultNode
from netdox.plugins.xenorchestra.objs import XOServer, Pool, Host, VirtualMachine
from datetime import datetime

logger = logging.getLogger(__name__)

##################
# User functions #
##################

def runner(network: Network) -> list[Pool]:
    """
    Generates VirtualMachine and Host instances and adds them to the network.
    
    :param network: The network
    :type network: Network
    :return: A list of Pool objects.
    :rtype: list[Pool]
    """
    return asyncio.run(get_vms(network))
    

async def get_vms(network: Network) -> list[Pool]:
    """
    Gets VM info from XenOrchestra.

    :param network: The network.
    :type network: Network
    :return: Dict mapping host machine IPs to their hosted VMs.
    :rtype: dict[str, list[VirtualMachine]]
    """
    async with XOServer(**utils.config('xenorchestra')) as xo:
        pool_data = xo.fetchObjs({'type': 'pool'})
        host_data = xo.fetchObjs({'type': 'host'})
        vm_data = xo.fetchObjs({'type': 'VM'})
        snapshot_data = await xo.fetchObjs({'type': 'VM-snapshot'})

        pools: dict[str, Pool] = {}
        for uuid, data in (await pool_data).items():
            pools[uuid] = Pool(uuid, data['name_label'], {})
        
        for uuid, data in (await host_data).items():
            node = DefaultNode(network, name = data['name_label'], private_ip = data['address'])
            pools[data['$pool']].hosts[uuid] = (Host(uuid, data['name_label'], node, {}))

        # snapshot_data = (await snapshot_data)
        for uuid, data in (await vm_data).items():
            if data['power_state'] != 'Running':
                continue

            if 'mainIpAddress' not in data:
                logger.warning(f'VM {data["name_label"]} has no IP address')
                continue

            snapshot_dts = []
            if 'snapshots' in data:
                for snapshot_id in data['snapshots']:
                    snapshot_dts.append(datetime.fromtimestamp(snapshot_data[snapshot_id]['snapshot_time']))                    

            pool = pools[data['$pool']]
            host = pool.hosts[data['$container']]

            host.vms[uuid] = VirtualMachine(
                network = network,
                name = data['name_label'],
                desc = data['name_description'],
                uuid = uuid,
                template = data['other']['base_template_name'] if 'base_template_name' in data['other'] else '—',
                os = data['os_version'],
                host = host.node.private_ip,
                pool = pool.name,
                snapshots = snapshot_dts,
                private_ip = data['mainIpAddress'],
                tags = data['tags']
            )
    
    return list(pools.values())

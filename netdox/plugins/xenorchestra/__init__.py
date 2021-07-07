"""
Used to read and modify the VMs managed by Xen Orchestra
"""
from __future__ import annotations

import json
import os
import random
from functools import wraps
from textwrap import dedent
from typing import Iterable

import utils
import websockets
from networkobjs import Network, NetworkObject, Node
from plugins import Plugin as BasePlugin

##################################
# Generic websocket interactions #
##################################

async def call(method: str, params: dict = {}, notification: bool = False) -> dict:
    """
    Makes a call with some given method and params, returns a JSON object

    :Args:
        method:
            The RPC method to call
        params:
            A dictionary of parameters to call the method with
        notification:
            If true no response is expected and no ID is sent

    :Returns:
        The JSON returned by the server
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
    @wraps(func)
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
async def reciever(id: int) -> dict:
    """
    Consumes responses sent by websocket server, returns the one with the specified ID.

    :Args:
        id:
            The ID generated alongside the outgoing message which identifies the response message
    
    :Returns:
        The JSON returned by the server
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


##################
# Public objects #
##################

## Nodes

class VirtualMachine(Node):
    """
    A VM running in XenOrchestra

    :param name: The name of the VM
    :type name: str
    :param desc: A brief description of the VMs purpose
    :type desc: str
    :param uuid: A unique alphanumeric identifier
    :type uuid: str
    :param template: The template the VM was created from
    :type template: str
    :param os: A dictionary of information about the VMs operating system, returned by the xo-server API under the key 'os_version'
    :type os: dict
    :param host: The uuid of the XenOrchestra Host this VM is running on
    :type host: str
    :param pool: The name of the pool this VMs host is in
    :type pool: str
    :param private_ip: The private IP address this VM has been assigned via VIF
    :type private_ip: str
    :param public_ips: Some public ips to associate with this VM, defaults to None
    :type public_ips: Iterable[str], optional
    :param domains: Some domains to associate with this VM, defaults to None
    :type domains: Iterable[str], optional
    """
    uuid: str
    pool: str
    host: str
    

    def __init__(self, 
            name: str,
            desc: str, 
            uuid: str,
            template: str,
            os: dict,
            host: str, 
            pool: str,
            private_ip: str,
            public_ips: Iterable[str] = None,
            domains: Iterable[str] = None
        ) -> None:
        
        super().__init__(name, private_ip, public_ips, domains, 'XenOrchestra VM')

        self.desc = desc.strip()
        self.uuid = uuid.strip().lower()
        self.docid = f'_nd_node_xovm_{self.uuid}'
        self.template = template
        self.os = os
        self.host = host.strip().lower()
        self.pool = pool.strip().lower()

    def merge(self, object: NetworkObject) -> VirtualMachine:
        self.public_ips = self.public_ips.union(set(object.public_ips))
        self.domains = self.domains.union(set(object.domains))
        self.network = object.network
        return self


class Host(Node):
    """
    A host running XenOrchestra VMs
    """
    
    def __init__(self, 
            name: str, 
            desc: str,
            uuid: str,
            cpus: dict,
            bios: dict,
            vms: Iterable[str],
            pool: str,
            private_ip: str, 
            public_ips: Iterable[str] = None, 
            domains: Iterable[str] = None
        ) -> None:

        super().__init__(name, private_ip, public_ips, domains, 'XenOrchestra Host')

        self.desc = desc.strip()
        self.uuid = uuid.strip().lower()
        self.docid = f'_nd_node_xohost_{self.uuid}'
        self.cpus = cpus
        self.bios = bios
        self.vms = set(vms)
        self.pool = pool.strip().lower()

    def merge(self, object: NetworkObject) -> Host:
        self.public_ips = self.public_ips.union(set(object.public_ips))
        self.domains = self.domains.union(set(object.domains))
        self.network = object.network
        return self


## Plugin

from plugins.xenorchestra.fetch import runner


class Plugin(BasePlugin):
    name = 'xenorchestra'
    stages = ['nodes']
    xslt = 'plugins/xenorchestra/nodes.xslt'

    def init(self) -> None:
        """
        Some initialisation for the plugin to work correctly

        :meta private:
        """
        global creds
        creds = utils.config()['plugins']['xenorchestra']
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

    def runner(self, network: Network, *_) -> None:
        runner(network)

"""
Used to read and modify the VMs managed by Xen Orchestra
"""
from __future__ import annotations

import json
import os
import random
from functools import wraps
from textwrap import dedent

import iptools
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
    """
    uuid: str
    pool: str
    host: str

    def __init__(self, 
            name: str,
            desc: str, 
            uuid: str,
            private_ip: str = None,
            domains: set = None,
            template: str = None,
            os: dict = None,
            host: str = None, 
            pool: str = None,) -> None:
        if private_ip and iptools.valid_ip(private_ip):
            self.private_ip = private_ip
        elif private_ip:
            raise ValueError(f'Invalid private IP: {private_ip}')

        self.name = name.lower()
        self.desc = desc
        self.uuid = uuid.lower()
        self.docid = f'_nd_node_xovm_{self.uuid}'
        self.private_ip = private_ip
        self.domains = set(domains) if domains else set()
        self.template = template
        self.os = os or {}
        self.host = host.lower() if host else None
        self.pool = pool

        self.type = 'XenOrchestra VM'

    @property
    def ips(self) -> list[str]:
        return [self.private_ip]

    def merge(self, object: NetworkObject) -> VirtualMachine:
        if isinstance(object, VirtualMachine):
            raise NotImplementedError('Merging VMs is not implemented yet')
        else:
            self.network = object.network
            self.private_ip = object.private_ip
            self.domains = list(set(self.domains))

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

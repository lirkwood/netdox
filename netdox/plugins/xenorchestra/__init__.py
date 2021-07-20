"""
Used to read and modify the VMs managed by Xen Orchestra
"""
from __future__ import annotations

import json
import os
import random
from functools import wraps
from typing import Iterable

import psml
import utils
import websockets
from bs4 import Tag
from networkobjs import Network, NetworkObject, Node
from plugins import Plugin as BasePlugin

##################################
# Generic websocket interactions #
##################################

async def call(method: str, params: dict = {}, notification: bool = False) -> dict:
    """
    Makes a call with some given method and params, returns a JSON object

    :param method: The method to use with the call
    :type method: str
    :param params: Some params to pass to the method, defaults to {}
    :type params: dict, optional
    :param notification: Whether or not to expect a response, True if no response expected, defaults to False
    :type notification: bool, optional
    :return: A dictionary containing the response sent by the websocket server.
    :rtype: dict
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

    :param id: The ID of the message to return
    :type id: int
    :return: A dictionary containing a response from the websocket server.
    :rtype: dict
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
    A VM running in XenOrchestra.
    """
    desc: str
    """Brief description of this VM's purpose."""
    uuid: str
    """Unique identifier assigned by XenOrchestra."""
    template: str
    """The template the VM was cloned from."""
    os: dict
    """Dictionary of info about the VM's operating system."""
    pool: str
    """The name of the pool the VM's Host belongs to."""
    host: str
    """The UUID of the Host the VM is running on."""

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
    
    @property
    def psmlCore(self) -> Tag:
        """
        Core fragment of the VirtualMachine Node document

        :return: A *properties-fragment* bs4 tag
        :rtype: Tag
        """
        frag = Tag(is_xml = True, name = 'properties-fragment', attrs={'id':'core'})
        frag.append(psml.property(
            name='description', title='Description', value=self.desc
        ))
        frag.append(psml.property(
            name='uuid', title='UUID', value=self.uuid
        ))
        frag.append(psml.propertyXref(
            name='host', title='Host Machine', docid=f'_nd_node_xohost_{self.host}'
        ))
        return frag
    
    @property
    def psmlOS(self) -> Tag:
        """
        OS fragment of the VirtualMachine Node document

        :return: A *properties-fragment* bs4 tag
        :rtype: Tag
        """
        frag = Tag(is_xml = True, name = 'properties-fragment', attrs={'id':'os_version'})
        frag.append(psml.property(
            name='os-name', title='OS name', value=self.os['name']
        ))
        frag.append(psml.property(
            name='os-uname', title='OS uname', value=self.os['uname']
        ))
        frag.append(psml.property(
            name='os-distro', title='Distro', value=self.os['distro']
        ))
        frag.append(psml.property(
            name='os-major', title='Major version', value=self.os['major']
        ))
        frag.append(psml.property(
            name='os-minor', title='Minor version', value=self.os['minor']
        ))
        return frag

    @property
    def psmlBody(self) -> Iterable[Tag]:
        section = Tag(is_xml=True, name='section', attrs={'id':'body'})
        section.append(self.psmlCore)
        section.append(self.psmlOS)
        return [section]


class Host(Node):
    """
    A host running XenOrchestra VMs
    """
    desc: str
    """Brief description of this Host's purpose."""
    uuid: str
    """Unique identifier assigned by XenOrchestra."""
    cpus: dict
    """Dictionary containing some info about this Host's CPUs."""
    bios: dict
    """Dictionary containing some info about this Host's BIOS."""
    vms: set
    """Set of UUIDs of VMs running on this Host."""
    pool: str
    """The name of the pool this Host belongs to."""
    
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

    @property
    def psmlCore(self) -> Tag:
        """
        Core fragment of the Host Node document.

        :return: A *properties-fragment* bs4 tag.
        :rtype: Tag
        """
        frag = Tag(is_xml = True, name = 'properties-fragment', attrs={'id':'core'})
        frag.append(psml.property(
            name='description', title='Description', value=self.desc
        ))
        frag.append(psml.property(
            name='uuid', title='UUID', value=self.uuid
        ))
        frag.append(psml.propertyXref(
            name='pool', title='Pool', value=self.pool
        ))

    @property
    def psmlCPUs(self) -> Tag:
        """
        Core fragment of the Host Node document.

        :return: A *properties-fragment* bs4 tag.
        :rtype: Tag
        """
        frag = Tag(is_xml = True, name = 'properties-fragment', attrs={'id':'cpus'})
        frag.append(psml.property(
            name='cpu-count', title='CPU count', value=self.cpus['cpu_count']
        ))
        frag.append(psml.property(
            name='cpu-socket-count', title='CPU sockets', value=self.cpus['socket_count']
        ))
        frag.append(psml.property(
            name='cpu-vendor', title='CPU vendor', value=self.cpus['vendor']
        ))
        frag.append(psml.property(
            name='cpu-speed', title='CPU speed', value=self.cpus['speed']
        ))
        frag.append(psml.property(
            name='cpu-model', title='CPU model', value=self.cpus['modelname']
        ))

    @property
    def psmlBody(self) -> Iterable[Tag]:
        section = Tag(is_xml=True, name='section', attrs={'id':'body'})
        section.append(self.psmlCore)
        section.append(self.psmlCPUs)
        return [section]


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

        for type in ('poolHosts', 'templates'):
            utils.jsonForXslt(f'plugins/xenorchestra/src/{type}.xml', f'{type}.json')

    def runner(self, network: Network, *_) -> None:
        runner(network)

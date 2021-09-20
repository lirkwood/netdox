"""
Used to read and modify the VMs managed by Xen Orchestra
"""
from __future__ import annotations

import json
import logging
import os
import random
from functools import wraps
from typing import Iterable

import websockets
from bs4 import Tag

from netdox import psml, utils
from netdox.objs import DefaultNode, Network
from netdox.objs.nwobjs import IPv4Address

logging.getLogger('websockets').setLevel(logging.INFO)

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

class VirtualMachine(DefaultNode):
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
    hostIp: IPv4Address
    """The IPv4 address of the node this VM is hosted on."""
    type: str = 'XenOrchestra VM'

    def __init__(self, 
            network: Network,
            name: str,
            desc: str, 
            uuid: str,
            template: str,
            os: dict,
            host: str, 
            pool: str,
            private_ip: str,
            public_ips: Iterable[str] = [],
            domains: Iterable[str] = []
        ) -> None:
        
        super().__init__(network, name, private_ip, public_ips, domains)

        self.desc = desc.strip()
        self.uuid = uuid.strip().lower()
        self.template = template
        self.os = os
        self.hostIp = self.network.ips[host]
        self.pool = pool.strip().lower()
        
        self.network.addRef(self, self.uuid)
    
    @property
    def psmlCore(self) -> Tag:
        """
        Core fragment of the VirtualMachine Node document

        :return: A *properties-fragment* bs4 tag
        :rtype: Tag
        """
        return psml.PropertiesFragment('core', properties = [
            psml.Property(name='description', title='Description', value=self.desc),
            psml.Property(name='uuid', title='UUID', value=self.uuid),
            psml.Property(name='ipv4', title='Host IP', 
                xref_docid = '_nd_ip_'+ self.hostIp.name.replace('.','_')),
            psml.Property(name='host', title='Host Node', ref=self.hostIp.node.docid)
        ])
    
    @property
    def psmlOS(self) -> Tag:
        """
        OS fragment of the VirtualMachine Node document

        :return: A *properties-fragment* bs4 tag
        :rtype: Tag
        """
        return psml.PropertiesFragment('os_version', properties = [
            psml.Property(name='os-name', title='OS name', 
                value = self.os['name'] if 'name' in self.os else ''),

            psml.Property(name='os-uname', title='OS uname', 
                value = self.os['uname'] if 'uname' in self.os else ''),

            psml.Property(name='os-distro', title='Distro', 
                value = self.os['distro'] if 'distro' in self.os else ''),
                
            psml.Property(name='os-major', title='Major version', 
                value = self.os['major'] if 'major' in self.os else ''),

            psml.Property(name='os-minor', title='Minor version', 
                value = self.os['minor'] if 'minor' in self.os else '')
        ])

    @property
    def psmlBody(self) -> Iterable[Tag]:
        section = Tag(is_xml=True, name='section', attrs={'id':'body'})
        section.append(self.psmlCore)
        section.append(self.psmlOS)
        return [section]


## Plugin

from netdox.plugins.xenorchestra.fetch import runner
from netdox.plugins.xenorchestra.pub import genpub


def init() -> None:
    """
    Some initialisation for the plugin to work correctly

    :meta private:
    """
    global creds
    creds = utils.config('xenorchestra')
    global url
    url = f"wss://{creds['host']}/api/"
    if not os.path.exists(utils.APPDIR+ 'plugins/xenorchestra/src'):
        os.mkdir(utils.APPDIR+ 'plugins/xenorchestra/src')

global pubdict
pubdict = {}
def nodes(network: Network) -> None:
    global pubdict
    pubdict = runner(network)

def write(network: Network) -> None:
    genpub(network, pubdict)


__stages__ = {
    'nodes': nodes,
    'write': write
}

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
from networkobjs import Network, DefaultNode
from plugins import BasePlugin as BasePlugin

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
    host: str
    """A ref to the node this VM is hosted on."""
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
        self.host = host.strip().lower()
        self.pool = pool.strip().lower()
        
        self.network.addRef(self, self.uuid)
    
    @property
    def psmlCore(self) -> Tag:
        """
        Core fragment of the VirtualMachine Node document

        :return: A *properties-fragment* bs4 tag
        :rtype: Tag
        """
        frag = Tag(is_xml = True, name = 'properties-fragment', attrs={'id':'core'})
        frag.append(psml.newprop(
            name='description', title='Description', value=self.desc
        ))
        frag.append(psml.newprop(
            name='uuid', title='UUID', value=self.uuid
        ))
        frag.append(psml.newxrefprop(
            name='host', title='Host Machine', ref=self.network.nodes[self.host].docid
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
        frag.append(psml.newprop(
            name='os-name', title='OS name', value=self.os['name'] if 'name' in self.os else ''
        ))
        frag.append(psml.newprop(
            name='os-uname', title='OS uname', value=self.os['uname'] if 'uname' in self.os else ''
        ))
        frag.append(psml.newprop(
            name='os-distro', title='Distro', value=self.os['distro'] if 'distro' in self.os else ''
        ))
        frag.append(psml.newprop(
            name='os-major', title='Major version', value=self.os['major'] if 'major' in self.os else ''
        ))
        frag.append(psml.newprop(
            name='os-minor', title='Minor version', value=self.os['minor'] if 'minor' in self.os else ''
        ))
        return frag

    @property
    def psmlBody(self) -> Iterable[Tag]:
        section = Tag(is_xml=True, name='section', attrs={'id':'body'})
        section.append(self.psmlCore)
        section.append(self.psmlOS)
        return [section]


## Plugin

from plugins.xenorchestra.fetch import runner
from plugins.xenorchestra.pub import genpub


class Plugin(BasePlugin):
    name = 'xenorchestra'
    stages = ['nodes', 'pre-write']

    pubdict: dict
    """A dictionary describing the hierarchy from pools -> hosts -> vms"""

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

    def runner(self, network: Network, stage: str) -> None:
        if stage == 'nodes':
            self.pubdict = runner(network)
        else:
            try:
                genpub(network, self.pubdict)
            except AttributeError:
                print(
                    '[WARNING][xenorchestra] Failed to finish adding VirtualMachines to the network.',
                    'As a result no publication can be generated.'
                )
from __future__ import annotations

import json
from typing import Iterable, Optional

import ssl
import certifi
from netdox import DefaultNode, IPv4Address, Network, psml
from websockets import client
from websockets.exceptions import WebSocketException


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
    tags: set[str]
    """Set of tags assigned in XenOrchestra."""
    hostIp: IPv4Address
    """The IPv4 address of the node this VM is hosted on."""
    type: str = 'xovm'

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
            domains: Iterable[str] = [],
            tags: Iterable[str] = []
        ) -> None:
        
        super().__init__(network, name, private_ip, public_ips, domains)

        self.desc = desc.strip()
        self.uuid = uuid.strip().lower()
        self.template = template
        self.os = os
        self.hostIp = self.network.ips[host]
        self.pool = pool.strip().lower()
        self.tags = set(tags)
        
        self.network.nodes.addRef(self, self.uuid)
    
    @property
    def psmlCore(self) -> psml.PropertiesFragment:
        """
        Core fragment of the VirtualMachine Node document

        :return: A *properties-fragment* bs4 tag
        :rtype: Tag
        """
        return psml.PropertiesFragment('core', properties = [
            psml.Property(name='description', title='Description', value=self.desc),
            psml.Property(name='uuid', title='UUID', value=self.uuid),
            psml.Property(name='ipv4', title='Host IP', 
                value = psml.XRef(docid = '_nd_ipv4_'+ self.hostIp.name.replace('.','_'))),
            psml.Property(name='host', title='Host Node', 
                value = (
                    psml.XRef(docid = self.hostIp.node.docid))
                    if self.hostIp.node else '—'
                )
        ])
    
    @property
    def psmlOS(self) -> psml.PropertiesFragment:
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
    def psmlTags(self) -> psml.PropertiesFragment:
        """
        Tags fragment of the VirtualMachine Node document

        :return: A PropertiesFragment
        :rtype: Tag
        """
        return psml.PropertiesFragment('tags', [
            psml.Property('tag', tag, 'Tag')
            for tag in self.tags
        ])

    @property
    def psmlBody(self) -> list[psml.Section]:
        return [psml.Section('body', fragments = [
            self.psmlCore, self.psmlOS, self.psmlTags])]



class XOServer:
    url: str
    """URL of the server."""
    frames: dict
    """A dictionary of response frames from the server."""
    _frame_id: int
    """Current frame id."""
    _user: str
    """Username to login with."""
    _pass: str
    """Password to login with."""
    _socket: Optional[client.WebSocketClientProtocol]
    """Socket object."""

    def __init__(self, host: str, username: str, password: str) -> None:
        self.url = f"wss://{host}/api/"
        self.frames = {}
        self._frame_id = 0
        self._user, self._pass = username, password
        self._socket = None

    async def __aenter__(self) -> XOServer:
        ssl_context = ssl.create_default_context(cadata = certifi.contents())
        self._socket = await client.connect(
            self.url, 
            max_size = 3000000, 
            ssl = ssl_context,
            open_timeout = 30
        )

        if 'error' in await self.call('session.signInWithPassword', {
            'email': self._user, 
            'password': self._pass
        }):
            raise RuntimeError(f'Failed to sign in with user {self._user}')
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._socket = await self._socket.close()

    def _ensure_socket(self) -> client.WebSocketClientProtocol:
        """
        Returns the current socket, if it is open.
        Raises a WebSocketException otherwise.
        """
        if not self._socket: 
            raise WebSocketException(
                'Cannot send request to server before opening socket.')
        else:
            return self._socket

    async def call(self, method: str, params: dict = {}, notification: bool = False) -> dict:
        """
        Makes a call to some method with some params, returns a JSON object

        :param method: The method to use with the call
        :type method: str
        :param params: Some params to pass to the method, defaults to {}
        :type params: dict, optional
        :param notification: Whether or not to expect a response, True if no response expected, defaults to False
        :type notification: bool, optional
        :return: A dictionary containing the response sent by the websocket server.
        :rtype: dict
        """
        socket = self._ensure_socket()
        if notification:
            await socket.send(json.dumps({
                "jsonrpc": "2.0",
                "method": method,
                "params": params
            }))
            return {'notification': True}
        else:
            self._frame_id += 1
            id = f"netdox-{self._frame_id}"
            await socket.send(json.dumps({
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": id
            }))
            response = await self._receive(id)
            self._frame_id -= 1
            return response

    async def _receive(self, id: str) -> dict:
        """
        Consumes responses sent by websocket server, returns the one with the specified ID.

        :param id: The ID of the message to return
        :type id: int
        :return: A dictionary containing a response from the websocket server.
        :rtype: dict
        """
        socket = self._ensure_socket()
        if id in self.frames:
            return self.frames.pop(id)
        async for message_bytes in socket:
            message = json.loads(message_bytes)
            if 'id' in message:
                if message['id'] == id:
                    return message
                else:
                    self.frames[message['id']] = message
                    
        raise WebSocketException(
            f"Exhausted inbound messages from server, failed to match ID '{id}'")

    async def fetchObjs(self, filter: dict[str, str]) -> dict:
        """
        Returns a dict of all objects on the server that match *filter*.

        :param filter: A dict of attributes to filter objects by.
        :type filter: dict[str, str]
        :return: The "result" object in the JSON returned by the server.
        :rtype: dict
        """
        return (await self.call('xo.getAllObjects', {'filter': filter}))['result']

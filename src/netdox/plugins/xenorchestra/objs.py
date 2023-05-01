from __future__ import annotations

import json
from typing import Iterable, Optional

import ssl
import certifi
from netdox import Node, IPv4Address, Network, DefaultNode, psml
from websockets import client
from websockets.exceptions import WebSocketException
from datetime import datetime, date
from dataclasses import dataclass
from math import floor

@dataclass(eq = True, frozen = True)
class Remote:
    """A remote filesystem."""
    uuid: str
    """uuid of the remote."""
    name: str
    """name of the remote."""
    url: str
    """URL of the"""

@dataclass(eq = True, frozen = True)
class VMBackup:
    """A backup file for a VM."""
    uuid: str
    """uuid of the backup."""
    vm: str
    """uuid of backed up VM."""
    mode: str
    """mode the backup was performed in."""
    timestamp: datetime
    """Date and time the backup was performed."""
    remote: Remote
    """Remote filesystem this backup is stored on."""
    job: str
    """name of the job that triggered this backup."""

    def month(self) -> date:
        """Returns a datetime with the year and month this backup was performed."""
        return date(year = self.timestamp.year, month = self.timestamp.month, day = 1)

    @property
    def docid(self) -> str:
        return f'_nd_xobackup_{self.timestamp.year}-{self.timestamp.month}-{self.vm}'

    def to_frag(self) -> psml.PropertiesFragment:
        """Returns a psml PropertiesFragment describing this object."""
        return psml.PropertiesFragment(f'{self.timestamp.timestamp()}-{self.remote.uuid}', [
            psml.Property('job', self.job, 'Job Name'),
            psml.Property('uuid', self.uuid, 'Backup UUID'),
            psml.Property('mode', self.mode, 'Backup Mode'),
            psml.Property('timestamp', self.timestamp.isoformat(), 'Backup Timestamp', 'datetime'),
            psml.Property('remote_name', self.remote.name, 'Remote Filesystem Name'),
            psml.Property('remote_url', self.remote.url, 'Remote Filesystem URL')
        ])

@dataclass
class Pool:
    """A pool of VM hosts."""
    uuid: str
    """uuid of the pool"""
    name: str
    """name of the pool"""
    hosts: dict[str, Host]
    """Maps host uuids to object"""

@dataclass
class Host:
    """A machine hosting VMs."""
    uuid: str
    """uuid of the host"""
    name: str
    """name of the hose"""
    node: Node
    """node object describing host"""
    vms: dict[str, VirtualMachine]
    """Maps vm uuids to object"""

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
    snapshots: list[datetime]
    """Date and time of each snapshot for this VM."""
    backups: list[VMBackup]
    """Backups of this VM, sorted from oldest to newest."""
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
            snapshots: list[datetime],
            backups: list[VMBackup],
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
        self.snapshots = snapshots
        self.backups = backups
    
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
    def psmlSnapshots(self) -> psml.PropertiesFragment:
        """
        Snapshots fragment of the VirtualMachine Node document

        :return: A PropertiesFragment        
        :rtype: psml.PropertiesFragment
        """
        return psml.PropertiesFragment('snapshots', [
            psml.Property('snapshot', str(dt), 'Snapshot Date', 'datetime')
            for dt in self.snapshots
        ])

    @property
    def psmlBackups(self) -> psml.PropertiesFragment:
        """
        Monthly backups fragment of the VirtualMachine Node document.

        :return: A PropertiesFragment
        :rtype: psml.PropertiesFragment
        """
        frag = psml.PropertiesFragment('backups', [])
        if len(self.backups) == 0:
            return frag

        month = None
        for bkp in reversed(self.backups):
            if month is None or bkp.month() != month:
                month = bkp.month()
                frag.insert(psml.Property(
                    name = 'monthly_backup', 
                    value = psml.XRef(docid = bkp.docid), 
                    title = f'Backups for {month.year}-{month.month}'
                ))
        return frag

    @property
    def psmlBody(self) -> list[psml.Section]:
        return [psml.Section('body', fragments = [
            self.psmlCore, self.psmlOS, self.psmlTags, self.psmlSnapshots, self.psmlBackups
        ])]



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
            ssl = ssl_context
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

    async def fetchObjs(self, filter: dict[str, str] = None) -> dict:
        """
        Returns a dict of all objects on the server that match *filter*.

        :param filter: A dict of attributes to filter objects by.
        :type filter: dict[str, str]
        :return: The "result" object in the JSON returned by the server.
        :rtype: dict
        """
        return (await self.call('xo.getAllObjects', {'filter': filter or {}}))['result']

    async def fetchVMBackups(self) -> dict[str, set[VMBackup]]:
        """
        Returns a dict mapping VM uuid to a set of backups of that VM.

        :return: Dict mapping VM uuid to a set of VM backups.
        :rtype: dict[str, set[VMBackup]]
        """
        remotes: dict[str, Remote] = {}
        for remote_data in (await self.call('remote.getAll'))['result']:
            remotes[remote_data['id']] = Remote(
                uuid = remote_data['id'], 
                name = remote_data['name'], 
                url = remote_data['url']
            )
        
        job_names: dict[str, str] = {}
        for job_data in (await self.call('backupNg.getAllJobs'))['result']:
            job_names[job_data['id']] = job_data['name']
        
        vm_backups: dict[str, set[VMBackup]] = {}
        remote_backup_data = await self.call('backupNg.listVmBackups', {'remotes': list(remotes.keys())})
        for remote_id, remote_backups in remote_backup_data['result'].items():
            remote = remotes[remote_id]
            
            for vm_id, vm_backup_data in remote_backups.items():
                if vm_id not in vm_backups:
                    vm_backups[vm_id] = set()

                backup_set = vm_backups[vm_id]
                for backup_data in vm_backup_data:
                    job_name = job_names[backup_data['jobId']] \
                        if backup_data['jobId'] in job_names else 'Unknown job.'

                    backup_set.add(VMBackup(
                        uuid = backup_data['id'], 
                        vm = vm_id, 
                        mode = backup_data['mode'],
                        timestamp = datetime.fromtimestamp(floor(backup_data['timestamp'] / 1000)), #??? timestamp wrong
                        remote = remote,
                        job = job_name
                    ))

        return vm_backups

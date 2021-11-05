from typing import Iterable

from bs4 import Tag
from netdox import psml
from netdox import DefaultNode, IPv4Address, Network


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
    tags: list[str]
    """List of tags assigned in XenOrchestra."""
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
                value = psml.XRef(docid = '_nd_ip_'+ self.hostIp.name.replace('.','_'))),
            psml.Property(name='host', title='Host Node', 
                value = psml.XRef(docid = self.hostIp.node.docid))
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
    def psmlTags(self) -> Tag:
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
    def psmlBody(self) -> Iterable[Tag]:
        section = Tag(is_xml=True, name='section', attrs={'id':'body'})
        section.append(self.psmlCore)
        section.append(self.psmlOS)
        section.append(self.psmlTags)
        return [section]

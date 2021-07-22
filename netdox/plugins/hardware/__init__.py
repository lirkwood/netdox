import os
import re
import time
from typing import Iterable
import zipfile
from shutil import rmtree

import pageseeder
import psml
import requests
import utils
from bs4 import BeautifulSoup, Tag
from networkobjs import IPv4Address, Network, Node
from plugins import Plugin as BasePlugin


class HardwareNode(Node):
    origin_doc: str

    def __init__(self, name: str, private_ip: str, psml: str, origin_doc: str, public_ips: Iterable[str] = None, domains: Iterable[str] = None) -> None:
        super().__init__(name, private_ip, public_ips=public_ips, domains=domains, type='Hardware Node')
        self.docid = f'_nd_node_hardware_{self.private_ip.replace(".","_")}'

        self.psml = psml
        self.origin_doc = origin_doc

    @property
    def outpath(self) -> str:
        return os.path.abspath(f'out/hardware/{self.docid}.psml')

    @property
    def psmlBody(self) -> Iterable[Tag]:
        return [self.psml]

    def merge(self, node: Node) -> Node:
        """
        Only merges if *node* has type 'default'.
        Otherwise adds an xref to ``self.origin_doc`` in the footer of *node* and returns it.

        :param node: The Node to merge with.
        :type node: Node
        :raises TypeError: If the node to merge with is not of 'default' type or has a different private_ip attribute.
        :return: This Node object, which is now a superset of the two.
        :rtype: Node
        """
        if node.private_ip == self.private_ip and node.type == 'default':
            self.psmlFooter += node.psmlFooter
            self.public_ips |= node.public_ips
            self.domains |= node.domains
            if node.network:
                self.network = node.network
            return self
        elif node.private_ip == self.private_ip:
            node.psmlFooter += psml.newxrefprop(
                'hardware', 'Hardware Info', self.origin_doc, reftype = 'uriid'
            )
            return node
        else:
            raise TypeError('Cannot merge two Nodes of different private ips')


class Plugin(BasePlugin):
    name = 'hardware'
    stages = ['nodes']
    thread: str
    """The thread tag returned by PageSeeder when starting the download."""

    def init(self) -> None:
        if os.path.exists('plugins/hardware/src'):
            rmtree('plugins/hardware/src')
        os.mkdir('plugins/hardware/src')

        self.thread = BeautifulSoup(
            pageseeder.export({'path': f'/{utils.config()["pageseeder"]["group"].replace("-","/")}/website/hardware'}, True)
        , features = 'xml')

    def runner(self, network: Network, stage: str) -> None:
        if stage == 'nodes':
            ## Downloading and unzipping the archive exported in init
            psconf = utils.config()["pageseeder"]

            try:
                while self.thread.thread['status'] != 'completed':
                    time.sleep(2)
                    self.thread = BeautifulSoup(pageseeder.get_thread(self.thread.thread['id']), features='xml')
            except AttributeError:
                pass
        
            with requests.get(
                f'https://{psconf["host"]}/ps/member-resource/{psconf["group"]}/{self.thread.zip.string}',
                headers = {'authorization': f'Bearer {pageseeder.token(psconf)}'},
                stream = True
            ) as zipResponse:
                zipResponse.raise_for_status()
                with open('plugins/hardware/src/hardware.zip', 'wb') as stream:
                    for chunk in zipResponse.iter_content(8192):
                        stream.write(chunk)
                    
            zip = zipfile.ZipFile('plugins/hardware/src/hardware.zip')
            zip.extractall('plugins/hardware/src')

            for file in utils.fileFetchRecursive('plugins/hardware/src'):
                if file.endswith('.psml'):
                    with open(file, 'r') as stream:
                        soup = BeautifulSoup(stream.read(), features = 'xml')
                        
                    section = soup.find('section', id='info')
                    if section:
                        ## For every file matching the structure (is psml, has section with id 'info')
                        ## Must be one 'name' and one 'ipv4' property at least.
                        name, ip = '', ''
                        for property in section.find_all('property'):
                            if property['name'] == 'ipv4':
                                if hasattr(property, 'value'):
                                    ip = property['value']
                                elif hasattr(property, 'datatype'):
                                    ip = re.search(r'_nd_ip_(?P<ip>.*)$', property.xref['docid'])['ip']
                            elif property['name'] == 'name':
                                name = property['value'].replace(' ','_')
                        
                        ## if minimum requirements met
                        if name and ip:
                            if ip not in network.ips:
                                network.add(IPv4Address(ip))

                            oldNode = network.ips[ip].node.docid if network.ips[ip].node is not None else ''
                            network.replace(oldNode, HardwareNode(
                                name = name,
                                private_ip = ip,
                                psml = ''.join([str(f) for f in section('properties-fragment')]),
                                origin_doc = soup.document['id']
                            ))
                            ## revisit
                            
                        else:
                            print(f'[DEBUG][hardware] Hardware document with URIID \'{soup.document["id"]}\'',
                            ' is missing property with name \'name\' or \'ipv4\' in section \'info\'.')
                    else:
                        print(f'[DEBUG][hardware] Hardware document with URIID \'{soup.document["id"]}\' has no section \'info\'.')
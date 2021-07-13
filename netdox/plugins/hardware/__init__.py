import os
import re
import time
from typing import Iterable
import zipfile
from shutil import rmtree

import pageseeder
import requests
import utils
from bs4 import BeautifulSoup
from networkobjs import IPv4Address, Network, Node
from plugins import Plugin as BasePlugin
from xml.sax.saxutils import escape


class HardwareNode(Node):
    psml: str
    origin_doc: str
    xslt = 'plugins/hardware/hardware.xslt'

    def __init__(self, name: str, private_ip: str, psml: str, origin_doc: str, public_ips: Iterable[str] = None, domains: Iterable[str] = None) -> None:
        super().__init__(name, private_ip, public_ips=public_ips, domains=domains, type='Hardware Node')
        self.psml = psml
        self.origin_doc = origin_doc

class Plugin(BasePlugin):
    name = 'hardware'
    stages = ['nodes']
    zipfile: str

    def init(self) -> None:
        psconf = utils.config()["pageseeder"]

        if os.path.exists('plugins/hardware/src'):
            rmtree('plugins/hardware/src')
        os.mkdir('plugins/hardware/src')

        thread = BeautifulSoup(
            pageseeder.export({'path': f'/{psconf["group"].replace("-","/")}/website/hardware'}, True)
        , features = 'xml')

        while thread.thread['status'] != 'completed':
            time.sleep(2)
            thread = BeautifulSoup(pageseeder.get_thread(thread.thread['id']), features='xml')
        
        with requests.get(
            f'https://{psconf["host"]}/ps/member-resource/{psconf["group"]}/{thread.zip.string}',
            headers = {'authorization': f'Bearer {pageseeder.token(psconf)}'},
            stream = True
        ) as zipResponse:
            zipResponse.raise_for_status()
            with open('plugins/hardware/src/hardware.zip', 'wb') as stream:
                for chunk in zipResponse.iter_content(8192):
                    stream.write(chunk)
                    
        zip = zipfile.ZipFile('plugins/hardware/src/hardware.zip')
        zip.extractall('plugins/hardware/src')

    def runner(self, network: Network, stage: str) -> None:
        if stage == 'nodes':
            for file in utils.fileFetchRecursive('plugins/hardware/src'):
                if file.endswith('.psml'):
                    with open(file, 'r') as stream:
                        soup = BeautifulSoup(stream.read(), features = 'xml')
                        
                    section = soup.find('section', id='info')
                    if section:

                        name, ip = '', ''
                        for property in section.find_all('property'):
                            if property['name'] == 'ipv4':
                                if hasattr(property, 'value'):
                                    ip = property['value']
                                elif hasattr(property, 'datatype'):
                                    ip = re.search(r'_nd_ip_(?P<ip>.*)$', property.xref['docid'])['ip']
                            elif property['name'] == 'name':
                                name = property['value']
                        
                        if name and ip:
                            if ip not in network.ips:
                                network.add(IPv4Address(ip))

                            oldNode = network.ips[ip].node
                            newNode = HardwareNode(
                                name = name,
                                private_ip = ip,
                                psml = escape(''.join([str(f) for f in section('properties-fragment')])),
                                origin_doc = soup.document['id']
                            )

                            if oldNode and oldNode.type == 'default':
                                network.replace(oldNode.docid, newNode)
                            elif not oldNode:
                                network.add(newNode)
                            else:
                                print(f'[WARNING][hardware] Cannot overwrite non-default node with ip {ip}')
                        else:
                            print('[DEBUG][hardware] Doc has no name or ip')
                    else:
                        print('[DEBUG][hardware] Doc has no section info')
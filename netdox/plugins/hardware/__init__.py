from __future__ import annotations

import os
import re
import time
import zipfile
from shutil import rmtree
from traceback import print_exc
from typing import Iterable

import requests
from bs4 import BeautifulSoup, Tag

from netdox import utils, pageseeder
from netdox.objs import DefaultNode, IPv4Address, Network


class HardwareNode(DefaultNode):
    origin_doc: str
    """The URI of the document this Node was created from."""
    filename: str
    """The filename to give this Node."""
    type: str = 'Hardware Node'

    def __init__(self, 
            network: Network,
            name: str, 
            private_ip: str, 
            psml: Tag, 
            origin_doc: str, 
            filename: str,
            domains: Iterable[str] = []
        ) -> None:
        super().__init__(network, name, private_ip, domains = domains)

        self.psml = psml
        self.origin_doc = origin_doc
        self.filename = filename

    @property
    def outpath(self) -> str:
        return os.path.normpath(os.path.abspath(utils.APPDIR+ f'out/hardware/{self.filename}'))

    @property
    def psmlBody(self) -> Iterable[Tag]:
        return [self.psml]

global thread
thread = None
def init() -> None:
    global thread
    if os.path.exists(utils.APPDIR+ 'plugins/hardware/src'):
        rmtree(utils.APPDIR+ 'plugins/hardware/src')
    os.mkdir(utils.APPDIR+ 'plugins/hardware/src')

    thread = BeautifulSoup(
        pageseeder.export({'path': f'/{utils.config()["pageseeder"]["group"].replace("-","/")}/website/hardware'}, True), 
    features = 'xml').thread

    while thread['status'] != 'completed':
        time.sleep(0.5)
        thread = BeautifulSoup(pageseeder.get_thread_progress(thread['id']), features='xml').thread
        if thread is None:
            raise RuntimeError('Thread for hardware download never had status \'completed\'')


def runner(network: Network) -> None:
    global thread
    ## Downloading and unzipping the archive exported in init
    psconf = utils.config()["pageseeder"]

    with requests.get(
        f'https://{psconf["host"]}/ps/member-resource/{psconf["group"]}/{thread.zip.string}',
        headers = {'authorization': f'Bearer {pageseeder.token(psconf)}'},
        stream = True
    ) as zipResponse:
        zipResponse.raise_for_status()
        with open(utils.APPDIR+ 'plugins/hardware/src/hardware.zip', 'wb') as stream:
            for chunk in zipResponse.iter_content(8192):
                stream.write(chunk)
            
    zip = zipfile.ZipFile(utils.APPDIR+ 'plugins/hardware/src/hardware.zip')
    zip.extractall(utils.APPDIR+ 'plugins/hardware/src')

    for file in utils.fileFetchRecursive(utils.APPDIR+ 'plugins/hardware/src'):
        try:
            if file.endswith('.psml'):
                with open(utils.APPDIR+ file, 'r', encoding = 'utf-8') as stream:
                    soup = BeautifulSoup(stream.read(), features = 'xml')
                    
                section = soup.find('section', id='info')
                if section:
                    ## For every file matching the structure (is psml, has section with id 'info')
                    ## Must be one 'name' and one 'ipv4' property at least.
                    name, ip = '', ''
                    for property in section.find_all('property'):
                        if property['name'] == 'ipv4':
                            if 'value' in property.attrs:
                                ip = property['value']
                            elif ( 
                                'datatype' in property.attrs
                                and property['datatype'] == 'xref'
                                and property.xref
                            ):
                                ip = re.search(r'_nd_ip_(?P<ip>.*)$', property.xref['docid'])['ip'].replace('_','.')
                        elif property['name'] == 'name':
                            name = property['value'].replace(' ','_')
                    
                    ## if minimum requirements met
                    if name and ip:
                        if ip not in network.ips:
                            IPv4Address(network, ip)

                        HardwareNode(
                            network = network,
                            name = name,
                            private_ip = ip,
                            psml = section.extract(),
                            origin_doc = soup.document['id'],
                            filename = os.path.basename(file)
                        )
                        
                    else:
                        print(f'[DEBUG][hardware] Hardware document with URIID \'{soup.document["id"]}\'',
                        ' is missing property with name \'name\' or \'ipv4\' in section \'info\'.')
                else:
                    print(f'[DEBUG][hardware] Hardware document with URIID \'{soup.document["id"]}\' has no section \'info\'.')

        except Exception:
            print(f'[ERROR][hardware] Failed while processing document with filename \'{os.path.basename(file)}\'')
            print_exc()

__stages__ = {
    'nodes': runner
}
__nodes__ = [HardwareNode]
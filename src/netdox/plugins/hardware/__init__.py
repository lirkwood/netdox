"""
This plugin is intended to support manual entry of Node objects describing physical machines.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import time
import zipfile
from shutil import rmtree
from traceback import print_exc
from typing import Iterable, Optional

import requests
from bs4 import BeautifulSoup, SoupStrainer, Tag

from netdox import iptools, pageseeder, utils
from netdox import Network
from netdox.nodes import Node

logger = logging.getLogger(__name__)

INFO_SECTION = SoupStrainer('section', id = 'info')
URI_PATTERN: re.Pattern = re.compile(r'<uri\s+id="(?P<id>\d+)"')


class HardwareNode(Node):
    """
    A Node built from manual-entry data.
    """
    origin_doc: str
    """The URI of the document this Node was created from."""
    filename: str
    """The filename to give this Node."""
    type: str = 'hardware'

    def __init__(self, 
            network: Network,
            psml: BeautifulSoup, 
            origin_doc: str, 
            filename: str
        ) -> None:

        domains, ips = [], []
        name = None
        for property in psml('property'):
            if property['name'] == 'domain':
                domain = self._addrFromProperty(property)
                if domain and re.fullmatch(utils.dns_name_pattern, domain): 
                    domains.append(domain)
                elif domain:
                    logging.warn(f'Failed to add invalid domain \'{domain}\' to HardwareNode \'{filename}\'')

            elif property['name'] == 'ipv4':
                ip = self._addrFromProperty(property)
                if ip and iptools.valid_ip(ip): 
                    ips.append(ip)
                elif ip:
                    logging.warn(f'Failed to add invalid IPv4 \'{ip}\' to HardwareNode \'{filename}\'')

            elif property['name'] == 'name':
                name = property['value']

        super().__init__(
            network = network, 
            name = name if name else filename, 
            identity = os.path.splitext(filename)[0],
            domains = domains,
            ips = ips
        )

        self.psml = psml
        self.origin_doc = origin_doc
        self.filename = filename

    ## abstract properties

    @property
    def outpath(self) -> str:
        return os.path.normpath(os.path.abspath(utils.APPDIR+ f'out/hardware/{self.filename}'))

    @property
    def psmlBody(self) -> list[Tag]:
        return [self.psml]

    ## methods

    def _addrFromProperty(self, property: Tag) -> Optional[str]:
        """
        Extracts the name of the referenced DNS object from some psml property (as a bs4 Tag).

        :param property: A PSML property
        :type property: Tag
        :return: The name of the DNS object
        :rtype: str
        """
        if 'value' in property.attrs:
            return property['value']

        elif (
            'datatype' in property.attrs                and
            property['datatype'] == 'xref'              and
            property.xref                               and
            'unresolved' not in property.xref.attrs
        ):
            return property.xref['urititle']
        return None


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
    zip_location = getattr(thread, 'zip', None)
    if not zip_location or not zip_location.string:
        raise RuntimeError(
            'Failed to retrieve exported file location from PageSeeder.')
    
    else:
        ## Downloading and unzipping the archive exported in init
        psconf = utils.config()["pageseeder"]
        with requests.get(
            f'https://{psconf["host"]}/ps/member-resource/{psconf["group"]}/{zip_location.string}',
            headers = {'authorization': f'Bearer {pageseeder.token(psconf)}'},
            stream = True
        ) as zipResponse:
            zipResponse.raise_for_status()
            with open(utils.APPDIR+ 'plugins/hardware/src/hardware.zip', 'wb') as stream:
                for chunk in zipResponse.iter_content(8192):
                    stream.write(chunk)
                
        zip = zipfile.ZipFile(utils.APPDIR+ 'plugins/hardware/src/hardware.zip')
        zip.extractall(utils.APPDIR+ 'plugins/hardware/src')
        shutil.rmtree(utils.APPDIR+ 'plugins/hardware/src/META-INF')

    for file in utils.fileFetchRecursive(utils.APPDIR+ 'plugins/hardware/src'):
        filename = os.path.basename(file)
        try:
            if file.endswith('.psml'):
                with open(utils.APPDIR+ file, 'r', encoding = 'utf-8') as stream: # type: ignore # ???
                    content = stream.read()
                soup = BeautifulSoup(content, features = 'xml', parse_only = INFO_SECTION)
                uri = re.search(URI_PATTERN, content)
                assert uri is not None, 'Failed to parse URIID from hardware document '+ filename

                if soup:
                    HardwareNode(
                        network = network,
                        psml = soup,
                        origin_doc = uri['id'],
                        filename = filename
                    )
                    
                else:
                    logger.debug(f'Hardware document \'{filename}\' has no section \'info\'.')

        except Exception:
            logger.error(f'Failed while processing document with filename \'{filename}\'')
            print_exc()

__stages__ = {
    'nodes': runner
}
__nodes__ = [HardwareNode]

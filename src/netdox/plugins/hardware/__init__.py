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
from typing import Optional

import requests
from bs4 import BeautifulSoup, SoupStrainer, Tag

from netdox import iptools, pageseeder, utils
from netdox import Network
from netdox.nodes import Node
from netdox.psml import Section

logger = logging.getLogger(__name__)

INFO_SECTION = SoupStrainer('section', id = 'info')
URI_PATTERN: re.Pattern = re.compile(r'<uri\s+id="(?P<id>\d+)"')
SRCDIR = os.path.join(utils.APPDIR, 'plugins', 'hardware', 'src')
ZIP_PATH = os.path.join(SRCDIR, 'hardware.zip')


class HardwareNode(Node):
    """
    A Node built from manual-entry data.
    """
    psml: Section
    """The body section copied from the document on PS."""
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

        self.origin_doc = origin_doc
        self.filename = filename
        domains, ips = [], []
        name = None
        for property in psml('property'):
            if property['name'] == 'domain':
                domain = self._addrFromProperty(property)
                if domain and utils.valid_domain(domain): 
                    self.domains.append(domain)

            elif property['name'] == 'ipv4':
                ip = self._addrFromProperty(property)
                if ip and iptools.valid_ip(ip): 
                    self.ips.append(ip)

            elif property['name'] == 'name':
                name = property['value']

        super().__init__(
            network = network, 
            name = name if name else filename, 
            identity = os.path.splitext(filename)[0],
            domains = domains,
            ips = ips
        )

        self.psml = Section.from_tag(psml.section)

    ## abstract properties

    @property
    def outpath(self) -> str:
        return os.path.normpath(os.path.abspath(utils.APPDIR+ f'out/hardware/{self.filename}'))

    @property
    def psmlBody(self) -> list[Section]:
        return [self.psml]

    ## methods

    def _consume_addr_property(self, property: Tag) -> None:
        """
        Parses a DNS name from the given property and adds it to this node.
        Only stores the domain/ipv4 if it is a valid DNS name.

        :param property: The property to parse a domain/ipv4 address from.
        :type property: Tag
        """

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
thread: Optional[Tag] = None
def init() -> None:
    global thread
    if os.path.exists(SRCDIR):
        rmtree(SRCDIR)
    os.mkdir(SRCDIR)

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
            with open(SRCDIR + '/hardware.zip', 'wb') as stream:
                for chunk in zipResponse.iter_content(8192):
                    stream.write(chunk)
                
        zip = zipfile.ZipFile(ZIP_PATH)
        zip.extractall(SRCDIR)
        shutil.rmtree(SRCDIR + '/META-INF')

    for file in utils.path_list(SRCDIR):
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

"""
This plugin is intended to support manual entry of Node objects describing physical machines.
"""
from __future__ import annotations

import logging
import os
import re
from traceback import print_exc
from typing import Optional

from bs4 import BeautifulSoup, Tag

from netdox import iptools, utils
from netdox import Network
from netdox.app import LifecycleStage
from netdox.nodes import Node
from netdox.psml import Section

logger = logging.getLogger(__name__)

URI_PATTERN: re.Pattern = re.compile(r'<uri\s+id="(?P<id>\d+)"')
DOCS_DIR = os.path.join(utils.APPDIR, 'src', 'remote', 'hardware')

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
    title: str
    """The document title for this Node."""
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

        for property in psml.find_all('property'):
            if property['name'] == 'domain':
                domain = self._addrFromProperty(property)
                if domain and utils.valid_domain(domain): 
                    domains.append(domain)

            elif property['name'] == 'ipv4':
                ip = self._addrFromProperty(property)
                if ip and iptools.valid_ip(ip): 
                    ips.append(ip)

            elif property['name'] == 'name' and property.parent['id'] == 'header':
                    name = property['value']
            
        if not name:
            logger.warn(f'Hardware document {origin_doc} is missing name property.')

        super().__init__(
            network = network, 
            name = name if name else filename, 
            identity = os.path.splitext(filename)[0],
            domains = domains,
            ips = ips
        )

        try:
            title = psml.find('uri')['title']
        except AttributeError:
            title = None
        self.title = title or self.name

        try:
            info_raw = psml.find('section', id = 'info').extract()
            if not info_raw.has_attr('title'):
                info_raw['title'] = 'Editable Content'
            info = Section.from_tag(info_raw)
        except AttributeError:
            info = Section('info', 'Editable Content')
        self.psml = info

    ## abstract properties

    @property
    def outpath(self) -> str:
        return os.path.normpath(os.path.abspath(utils.APPDIR+ f'out/hardware/{self.filename}'))

    @property
    def psmlBody(self) -> list[Section]:
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
    
    def to_psml(self) -> BeautifulSoup:
        soup = super().to_psml()
        soup.find('uri')['title'] = self.title
        soup.find('fragment', id = 'title').find('heading', level = '1').string = self.title
        return soup


def runner(network: Network) -> None:
    if not os.path.exists(DOCS_DIR):
        raise RuntimeError('Hardware documents were not downloaded.')    

    for file in utils.path_list(DOCS_DIR):
        filename = os.path.basename(file)
        try:
            if file.endswith('.psml'):
                with open(utils.APPDIR+ file, 'r', encoding = 'utf-8') as stream: # type: ignore # ???
                    content = stream.read()
                soup = BeautifulSoup(content, features = 'xml')
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
    LifecycleStage.NODES: runner
}
__nodes__ = [HardwareNode]
__output__ = {'hardware'}

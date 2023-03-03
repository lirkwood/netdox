import json
import logging
import shutil
from datetime import date, timedelta
from typing import Optional, cast

from bs4 import BeautifulSoup, Tag
from lxml import etree
from netdox import pageseeder
from netdox import Network
from netdox.plugins.xenorchestra.objs import VirtualMachine, Pool
from netdox.utils import APPDIR

logger = logging.getLogger(__name__)


def genpub(network: Network, pools: list[Pool]) -> None:
    """
    Generates a publication linking pools to hosts to vms

    :param network: The network
    :type network: Network
    :param pools: A list of pools.
    :type pools: list[Pool]
   """
    pub = BeautifulSoup(PUB, 'xml')
    section = pub.find('section', id = 'pools')

    for poolnum, pool in enumerate(pools):
        heading = pub.new_tag('heading', level = 2)
        heading.string = pool.name
        section.append(heading)
        heading.wrap(pub.new_tag('fragment', id = f'heading_{poolnum}'))

        xfrag = pub.new_tag(name = 'xref-fragment', id = f'pool_{poolnum}')
        for host in pool.hosts.values():
            xfrag.append(pub.new_tag('blockxref', frag = 'default', type = 'embed', docid = host.node.docid))

            for vm in host.vms.values():
                xfrag.append(pub.new_tag('blockxref', frag = 'default', type = 'embed', docid = vm.docid, level = 1))
                
        section.append(xfrag)

    with open(APPDIR+ 'plugins/xenorchestra/src/xopub.psml', 'w') as stream:
        stream.write(pub.prettify())

    try:
        etree.XMLSchema(file = APPDIR + 'src/psml.xsd').assertValid(
            etree.parse(APPDIR+ 'plugins/xenorchestra/src/xopub.psml'))

    except etree.DocumentInvalid:
        logger.error('Publication validation failed.')

    else:
        shutil.copyfile(APPDIR + 'plugins/xenorchestra/src/xopub.psml',
            APPDIR + 'out/xopub.psml')


def genreport(network: Network) -> None:
    """
    Generates a section to add to the Daily Report,
    containing information about VMs that were started / stopped today.

    :param network: The network
    :type network: Network
    """
    started_search = json.loads(pageseeder.search({
        'pagesize': 999,
        'filters': ','.join([
            'pstype:document',
            'psdocumenttype:node',
            'psproperty-type:'+ VirtualMachine.type,
            f'pscreateddate:{date.today()}'
        ])}))

    stopped_search = json.loads(pageseeder.search({
        'pagesize': 999,
        'filters': ','.join([
            'pstype:document',
            'psdocumenttype:node',
            'psproperty-type:'+ VirtualMachine.type,
            'label:expires-' + (date.today() + timedelta(days = 30)).isoformat()
        ])}))

    report = BeautifulSoup(REPORT, 'xml')
    empty = 0
    newfrag: Tag = report.find('fragment', id='xovms_new')
    oldfrag: Tag = report.find('fragment', id='xovms_old')
    for frag, results in (
        (newfrag, started_search), 
        (oldfrag, stopped_search)
    ):
        for result in results['results']['result']:
            uriid = _parse_uriid(result)
            assert uriid, 'Failed to parse uriid from search result'

            frag.append(Tag(is_xml = True,
                name = 'blockxref', attrs = {
                    'frag': 'default',
                    'uriid': uriid
            }))
        
        if len(results['results']['result']) < 1:
            frag.decompose()
            empty += 1
    
    if empty < 2:
        network.report.addSection(str(report))

def _parse_uriid(result: dict) -> Optional[str]:
    """
    Parses the URIID of a document from a PageSeeder search result.
    """
    uriid = None
    for field in result['fields']:
        if field['name'] == 'psid':
            uriid = field['value']
            break
    return uriid


PUB = '''
<document level="portable" type="references">

    <documentinfo>
        <uri title="Xen Orchestra Pools" />
        <publication id="_nd_xo_pub" title="Xen Orchestra Pools" />
    </documentinfo>

    <section id="title">
        <fragment id="title">
            <heading level="1">Xen Orchestra Pools</heading>
        </fragment>
    </section>

    <section id="pools" />
    
</document>
'''

REPORT = '''
<section id="xovms" title="XenOrchestra VMs">
    <fragment id="xovms_new">
        <heading level="2">VMs Started Today</heading>
    </fragment>
    <fragment id="xovms_old">
        <heading level="2">VMs Stopped Today</heading>
    </fragment>
</section>
'''

if __name__ == '__main__':
    from sys import stdout
    logger.addHandler(logging.StreamHandler(stdout))
    logger.setLevel(logging.DEBUG)
    logger.debug('foo')
    genreport(Network.from_dump())
import json
import logging
import shutil
from datetime import date, timedelta
from typing import cast

from bs4 import BeautifulSoup, Tag
from lxml import etree
from netdox import pageseeder
from netdox import Network
from netdox.nwobjs import Node
from netdox.plugins.xenorchestra.vm import VirtualMachine
from netdox.utils import APPDIR

logger = logging.getLogger(__name__)


def genpub(network: Network, pubdict: dict[str, dict[str, list[str]]]) -> None:
    """
    Generates a publication linking pools to hosts to vms

    :param network: The network
    :type network: Network
    :param pubdict: A dictionary of node docids
    :type pubdict: dict[str, dict[str, list[Node]]]
    """
    pub = BeautifulSoup(PUB, 'xml')
    section = pub.find('section', id = 'pools')
    count = 0
    for pool, hosts in pubdict.items():
        heading = pub.new_tag('heading', level = 2)
        heading.string = pool
        section.append(heading)
        heading.wrap(pub.new_tag('fragment', id = f'heading_{count}'))

        xfrag = pub.new_tag(name = 'xref-fragment', id = f'pool_{count}')
        for hostip, vms in hosts.items():
            node = network.ips[hostip].node
            if node:
                xfrag.append(pub.new_tag('blockxref', frag = 'default', type = 'embed', docid = node.docid))
            else:
                placeholder = pub.new_tag('para')
                placeholder.string = hostip
                xfrag.append(placeholder)

            for vm_docid in vms:
                xfrag.append(pub.new_tag('blockxref', frag = 'default', type = 'embed', docid = vm_docid, level = 1))
                
        section.append(xfrag)
        count += 1

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
    search = json.loads(pageseeder.search({
        'filters': ','.join([
            'pstype:document',
            'psdocumenttype:node',
            'psproperty-type:'+ VirtualMachine.type,
            '-label:stale'
        ])}))

    sentencedToday = json.loads(pageseeder.search({
        'filters': ','.join([
            'pstype:document',
            'psdocumenttype:node',
            'psproperty-type:'+ VirtualMachine.type,
            'label:expires-' + (date.today() + timedelta(days = 30)).isoformat()
        ])}))
        
    psvms = {}
    for result in (search['results']['result'] + sentencedToday['results']['result']):
        for field in result['fields']:
            if field['name'] == 'psproperty-uuid':
                # first field is always uriid
                psvms[field['value']] = result['fields'][0]['value']
                break

    netvms = {}
    for node in network.nodes:
        if node.type == VirtualMachine.type:
            vm = cast(VirtualMachine, node)
            netvms[vm.uuid] = node.docid

    if psvms or netvms:
        report = BeautifulSoup(REPORT, 'xml')

        newfrag = report.find('fragment', id='xovms_new')
        for newvm in (set(netvms) - set(psvms)):
            logger.debug('Started VM; URIID ' + netvms[newvm])
            newfrag.append(Tag(is_xml = True,
                name = 'blockxref', attrs = {
                    'frag': 'default',
                    'docid': netvms[newvm]
            }))
            
        oldfrag = report.find('fragment', id='xovms_old')
        for oldvm in (set(psvms) - set(netvms)):
            logger.debug('Stopped VM; URIID ' + psvms[oldvm])
            oldfrag.append(Tag(is_xml = True,
                name = 'blockxref', attrs = {
                    'frag': 'default',
                    'uriid': psvms[oldvm]
            }))

        network.report.addSection(str(report))

    else:
        logger.debug('No VMs on local or PageSeeder')

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
    genreport(Network.fromDump())
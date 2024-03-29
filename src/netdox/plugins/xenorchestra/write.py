import json
import logging
import shutil
from datetime import date, timedelta
from typing import Optional
import os
import copy
from calendar import monthrange

from bs4 import BeautifulSoup, Tag
from lxml import etree
from netdox import pageseeder
from netdox import Network
from netdox.plugins.xenorchestra.objs import VirtualMachine, Pool, VMBackup
from netdox.utils import APPDIR, OUTDIR
from netdox.psml import Section

logger = logging.getLogger(__name__)

BACKUP_DIR = os.path.join(OUTDIR, 'xobackup')

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
            # Host nodes are created as placeholders. This lookup returns the node that replaced them, if any.
            host_node = network.nodes[host.node.identity]
            xfrag.append(pub.new_tag('blockxref', frag = 'default', type = 'embed', docid = host_node.docid))

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

def write_backups(network: Network) -> None:
    """
    Writes documents that describe the VM backups.

    :param network: The network.
    :type network: Network
    """
    for node in network.nodes:
        if isinstance(node, VirtualMachine):
            write_vm_backups(node)

MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June',
               'July', 'August', 'September', 'October', 'November', 'December']
def month_name(month: int) -> str:
    """Returns name of the month. 1 - January, 12 - December."""
    return MONTH_NAMES[month - 1]

def version_backup_file(docid: str):
    today = date.today()
    month, year = today.month - 1, today.year
    if month == 0:
        month = 12
        year -= 1

    pageseeder.version(docid, {
        'name': f'{year}-{str(month).zfill(2)}',
        'description': f'Backups for the month of {month_name(month)} {year}'
    })


def cell(text: Optional[str]) -> Tag:
    """Returns a cell tag."""
    tag = Tag(name = 'cell', is_xml=True)
    if text is not None:
        tag.string = text
    return tag

def write_vm_backups(vm: VirtualMachine) -> None:
    """
    Writes a document that describes a month of backups for a VM.

    :param vm: VM that backups are of.
    :type vm: VirtualMachine
    :param month_backups: List of backups that were all performed in one month, sorted by date/time.
    :type month_backups: list[VMBackup]
    """
    today = date.today()
    if today.day == 1:
        version_backup_file(vm.backup_docid)

    template = MONTH_BACKUPS\
        .replace('#!title', f'Backups for {vm.name}')\
        .replace('#!docid', vm.backup_docid)\
        .replace('#!vm-docid', vm.docid)\
        .replace('#!month', f'{month_name(today.month)} {today.year}')
    soup = BeautifulSoup(template, 'xml')

    days: dict[int, list[VMBackup]] = {
        day: [] for day in range(1, monthrange(today.year, today.month)[1] + 1)
    }
    for bkp in vm.backups:
        days[bkp.timestamp.day].append(bkp)

    table = soup.find('table')
    for day, bkps in days.items():
        row = Tag(name = 'row')
        day_cell = cell(str(day))

        if day > today.day:
            row.append(day_cell)
            row.append(cell('NO DATA YET'))
            for _ in range(3):
                row.append(cell(None))
            table.append(row) # type: ignore
            continue

        if len(bkps) == 0:
            row.append(day_cell)
            row.append(cell('NO BACKUPS'))
            for _ in range(3):
                row.append(cell(None))
            table.append(row) # type: ignore
            continue

        for bkp in bkps:
            _row = copy.copy(row)
            _row.append(copy.copy(day_cell))
            _row.append(cell(bkp.uuid))
            _row.append(cell(bkp.mode))
            _row.append(cell(bkp.timestamp.isoformat()))
            _row.append(cell(bkp.remote.url))
            table.append(_row) # type: ignore

    logger.debug(f'Writing xobackups for {vm.name}')
    outpath = os.path.join(BACKUP_DIR, f'{vm.backup_docid}.psml')
    with open(outpath, 'w', encoding = 'utf-8') as stream:
        stream.write(str(soup))

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

MONTH_BACKUPS = '''
<document level="portable" type="xobackup">
    <documentinfo>
        <uri docid="#!docid" title="#!title" />
    </documentinfo>

    <section id="title">
        <fragment id="1">
            <heading level="1">#!title</heading>
        </fragment>
        <properties-fragment id="details">
            <property name="vm" title="VM" datatype="xref">
                <xref docid="#!vm-docid" frag="default" />
            </property>
            <property name="month" title="Month" value="#!month" />
        </properties-fragment>
    </section>

    <section id="backups">
        <fragment id="backup-table">
            <table>
                <col part="header"/>
                <col/>
                <col/>
                <col/>
                <col/>

                <row part="header">
                    <cell>Day</cell>
                    <cell>UUID</cell>
                    <cell>Mode</cell>
                    <cell>Timestamp</cell>
                    <cell>Filesystem URL</cell>
                </row>
            </table>
        </fragment>
    </section>
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

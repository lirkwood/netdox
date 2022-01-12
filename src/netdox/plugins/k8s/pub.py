from collections import defaultdict
from typing import DefaultDict, cast

from bs4 import BeautifulSoup
from netdox import Network
from netdox.utils import APPDIR
from netdox.plugins.k8s.objs import App
import logging

logger = logging.getLogger(__name__)

def genpub(network: Network) -> None:
    workerApps: DefaultDict[str, DefaultDict[str, list]] = defaultdict(lambda: defaultdict(list))
    for node in network.nodes:
        if isinstance(node, App):
            for pod in node.pods:
                workerNode = network.find_dns(pod.workerIp).node
                if workerNode is not None:
                    workerApps[node.cluster.name][workerNode.docid].append(node.docid)

    sortedWorkerApps: dict[str, dict[str, list[str]]] = {}
    for cluster in workerApps:
        sortedWorkerApps[cluster] = {k: workerApps[cluster][k] for k in sorted(workerApps[cluster])}

    pub = BeautifulSoup(TEMPLATE, features='xml')
    section = pub.find('section', id = 'clusters')

    count = 0
    for cluster, workers in sortedWorkerApps.items():
        heading = pub.new_tag('heading', level = 1)
        heading.string = cluster
        section.append(heading)
        heading.wrap(pub.new_tag('fragment', id = f'heading_{count}'))

        xfrag = pub.new_tag('xref-fragment', id = f'cluster_{count}')
        for worker, apps in workers.items():
            xfrag.append(pub.new_tag('blockxref', frag = 'default', type = 'embed', docid = worker))

            for app_docid in apps:
                xfrag.append(pub.new_tag('blockxref', frag = 'default', type = 'embed', docid = app_docid, level = 1))
        section.append(xfrag)
        count += 1
    
    with open(APPDIR+ 'out/k8spub.psml', 'w') as stream:
        stream.write(pub.prettify())

TEMPLATE = '''
<document level="portable" type="references">
    <documentinfo>
        <uri title="Kubernetes Clusters" />
        <publication id="_nd_k8s_pub" title="Kubernetes Clusters" />
    </documentinfo>

    <section id="title">
        <fragment id="title">
            <heading level="1">Kubernetes Clusters</heading>
        </fragment>
    </section>

    <section id="clusters" />
</document>
'''

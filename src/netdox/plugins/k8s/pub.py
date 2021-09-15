from collections import defaultdict

from bs4 import BeautifulSoup
from netdox.objs import Network
from netdox.utils import APPDIR
import logging

logger = logging.getLogger(__name__)

def genpub(network: Network) -> None:
    workerApps = defaultdict(lambda: defaultdict(list))
    for node in network.nodes:
        if node.type == 'Kubernetes App':
            for pod in node.pods.values():
                if network.ips[pod['workerIp']].node:
                    pod['workerNode'] = network.ips[pod['workerIp']].node.docid
                    workerApps[node.cluster][pod['workerNode']].append(node.docid)

    for cluster in workerApps:
        workerApps[cluster] = {k: workerApps[cluster][k] for k in sorted(workerApps[cluster])}

    import json 
    logger.debug(json.dumps(workerApps, indent=2))

    pub = BeautifulSoup(TEMPLATE, features='xml')
    section = pub.find('section', id = 'clusters')

    count = 0
    for cluster, workers in workerApps.items():
        heading = pub.new_tag('heading', level = 1)
        heading.string = cluster
        section.append(heading)
        heading.wrap(pub.new_tag('fragment', id = f'heading_{count}'))

        xfrag = pub.new_tag('xref-fragment', id = f'cluster_{count}')
        for worker, apps in workers.items():
            xfrag.append(pub.new_tag('blockxref', frag = 'default', type = 'embed', docid = worker))

            for app in apps:
                xfrag.append(pub.new_tag('blockxref', frag = 'default', type = 'embed', docid = app, level = 1))
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

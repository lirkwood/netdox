from bs4 import BeautifulSoup
from netdox.utils import APPDIR

def genpub(pubdict: dict) -> None:
    pub = BeautifulSoup(TEMPLATE, features='xml')
    section = pub.find('section', id = 'clusters')

    count = 0
    for cluster, workers in pubdict.items():
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
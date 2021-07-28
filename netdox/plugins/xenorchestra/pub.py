from bs4 import BeautifulSoup
from networkobjs import Node, Network

def genpub(network: Network, pubdict: dict[str, dict[str, list[Node]]]) -> None:
    """
    Generates a publication linking pools to hosts to vms

    :param network: The network
    :type network: Network
    :param pubdict: A dictionary of node docids
    :type pubdict: dict[str, dict[str, list[Node]]]
    """
    pub = BeautifulSoup(TEMPLATE, features='xml')
    section = pub.find('section', id = 'pools')
    count = 0
    for pool, hosts in pubdict.items():
        heading = pub.new_tag('heading', level = 2)
        heading.string = pool
        section.append(heading)
        heading.wrap(pub.new_tag('fragment', id = f'heading_{count}'))

        xfrag = pub.new_tag(name = 'xref-fragment', id = f'pool_{count}')
        for host, vms in hosts.items():
            finalref = network.nodes[host].docid
            xfrag.append(pub.new_tag('blockxref', frag = 'default', type = 'embed', docid = finalref))

            for vm in vms:
                finalref = network.nodes[vm].docid
                xfrag.append(pub.new_tag('blockxref', frag = 'default', type = 'embed', docid = finalref, level = 1))
                
        section.append(xfrag)
        count += 1

    with open('out/xopub.psml', 'w') as stream:
        stream.write(pub.prettify())


TEMPLATE = '''
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
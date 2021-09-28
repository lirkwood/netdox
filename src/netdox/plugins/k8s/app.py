from typing import Iterable

from bs4 import Tag
from netdox import psml, utils
from netdox.objs import Domain, Network
from netdox.objs.nwobjs import Node


class App(Node):
    """
    Kubernetes app from a namespaced deployment
    """
    cluster: str
    """Cluster this app is running in"""
    paths: set[str]
    """Ingress paths that resolve to this node. 
    Only includes paths starting on domains that also resolve to a configured proxy IP."""
    labels: dict
    """Labels applied to the pods"""
    template: dict
    """Template pods are started from"""
    pods: dict[str, dict]
    """A dict of the pods running this app"""
    type: str = 'k8sapp'

    ## dunder methods

    def __init__(self, 
            network: Network,
            name: str, 
            cluster: str, 
            paths: Iterable[str] = None,
            labels: dict = None, 
            pods: dict = None, 
            template: dict = None
        ) -> None:

        domains = {p.split('/')[0] for p in sorted(paths, key = len)}
        for domain in list(domains):
            if domain in network.domains:
                for proxy in utils.config('k8s')[cluster]['proxies']:
                    if not network.resolvesTo(network.domains[domain], network.ips[proxy]):
                        domains.remove(domain)

            else:
                Domain(network, domain)       
        
        self.paths = {path for path in paths if path.split('/')[0] in domains}

        super().__init__(
            network = network, 
            name = name,
            identity = cluster +'_'+ name,
            domains = [],
            ips = []
        )
        
        self.paths = set(paths) if paths else set()
        self.cluster = cluster
        self.labels = labels or {}
        self.template = template or {}
        self.pods = pods or {}

    ## abstract properties
    
    @property
    def psmlBody(self) -> Iterable[Tag]:
        return [self.psmlPodTemplate, self.psmlRunningPods]

    ## properties

    @property
    def psmlPodTemplate(self) -> Tag:
        section = Tag(is_xml=True, name='section', attrs={'id':'template', 'title':'Pod Template'})
        count = 0
        for container, template in self.template.items():
            frag = psml.PropertiesFragment(id = 'container_' + str(count), properties = [
                    psml.Property(name = 'container', title = 'Container Name', value = container),
                    psml.Property(name = 'image', title = 'Image ID', value = template['image'])
            ])
            for volume, paths in self.template[container]['volumes'].items():
                frag.append(psml.Property(
                    name = 'pvc', 
                    title = 'Persistent Volume Claim', 
                    value = volume
                ))
                frag.append(psml.Property(
                    name = 'mount_path', 
                    title = 'Path in Container', 
                    value = paths['mount_path']
                ))
                frag.append(psml.Property(
                    name = 'sub_path', 
                    title = 'Path in PVC', 
                    value = paths['sub_path']
                ))

            section.append(frag)
            count += 1
        return section
                
    @property
    def psmlRunningPods(self) -> Tag:
        section = Tag(is_xml=True, name='section', attrs={'id':'pods', 'title':'Running Pods'})
        count = 0
        for pod in self.pods.values():
            section.append(psml.PropertiesFragment(id = 'pod_' + str(count), properties = [
                psml.Property(name = 'pod', title = 'Pod', value = pod['name']),

                psml.Property(name = 'ipv4', title = 'Worker IP', 
                    value = psml.XRef(docid = f'_nd_ip_{pod["workerIp"].replace(".","_")}')),

                psml.Property(name = 'rancher', title="Pod on Rancher", 
                    value = psml.Link(pod['rancher'])),

                psml.Property(name = 'worker_node', title = 'Worker Node', 
                    value = psml.XRef(docid = self.network.ips[pod["workerIp"]].node.docid))
            ]))
            count += 1
        return section

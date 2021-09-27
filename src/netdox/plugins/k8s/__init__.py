"""
Used to read and modify the deployments running on the configured clusters.
"""
from __future__ import annotations

import logging
import os
from collections import defaultdict
from typing import Iterable

import yaml
from bs4.element import Tag
from kubernetes import config
from kubernetes.client import ApiClient
from netdox import psml, utils
from netdox.objs import Domain, Network
from netdox.objs.nwobjs import Node

logging.getLogger('kubernetes').setLevel(logging.INFO)

##  Plugin functions

def initContext(context: str = None) -> ApiClient:
    """
    Load config and initialise an api client for given context

    :Args:
      context:
        The context (configured in ``config.json``) to initialise

    :Returns:
      An ApiClient object connected to the given context
    """
    config.load_kube_config(utils.APPDIR+ 'plugins/k8s/src/kubeconfig', context=context)
    return ApiClient()

## Node

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


from netdox.plugins.k8s.pub import genpub
from netdox.plugins.k8s.refresh import runner


def init() -> None:
    """
    Some initialisation for the plugin to work correctly

    :meta private:
    """
    # Create output dir
    for dir in ('out', 'src'):
        if not os.path.exists(utils.APPDIR+ f'plugins/k8s/{dir}'):
            os.mkdir(utils.APPDIR+ f'plugins/k8s/{dir}')

    auth = utils.config('k8s')
    with open(utils.APPDIR+ 'plugins/k8s/src/kubeconfig', 'w') as stream:
        clusters = []
        users = []
        contexts = []
        for contextName, details in auth.items():
            clusters.append({
                'cluster': {'server': f"https://{details['host']}/k8s/clusters/{details['clusterId']}"},
                'name': contextName
            })

            users.append({
                'name': contextName,
                'user': {'token': details['token']}
            })

            contexts.append({
                'context': {
                    'cluster': contextName,
                    'user': contextName
                },
                'name': contextName
            })

        stream.write(yaml.dump({
        'apiVersion': 'v1',
        'Kind': 'Config',
        'current-context': list(auth)[0],
        'clusters': clusters,
        'users': users,
        'contexts': contexts
        }))

def domainapps(network: Network) -> None:
    pathnodes = {}
    domainpaths = defaultdict(set)
    for node in network.nodes:
        if node.type == 'Kubernetes App':
            node: App
            for path in node.paths:
                domainpaths[path.split('/')[0]].add(path)
                pathnodes[path] = node
    
    for domain, paths in domainpaths.items():
        ## Add a pfrag of paths relevant to each domain
        network.domains[domain].psmlFooter.append(
            psml.PropertiesFragment(
                id = 'k8sapps',
                properties = [
                    psml.Property(
                        name = 'app', 
                        title = 'Path: ' + path[len(domain):], 
                        value = psml.XRef(docid = pathnodes[path].docid)
                    ) for path in paths
                ]
            )
        )

__stages__ = {
    'nodes': runner,
    'footers': domainapps,
    'write': genpub
}

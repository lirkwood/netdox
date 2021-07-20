"""
Used to read and modify the deployments running on the configured clusters.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Iterable
from bs4 import BeautifulSoup

from bs4.element import Tag

import pageseeder
import utils
import yaml
from flask import Response
from networkobjs import JSONEncoder, Network, NetworkObjectContainer, Node
from plugins import Plugin as BasePlugin
import psml

from kubernetes import config
from kubernetes.client import ApiClient

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
    config.load_kube_config('plugins/kubernetes/src/kubeconfig', context=context)
    return ApiClient()


## Node subclasses

class App(Node):
    """
    Kubernetes app from a namespaced deployment
    """
    cluster: str
    labels: dict
    template: dict
    pods: dict
    _container: NetworkObjectContainer

    def __init__(self, 
            name: str, 
            domains: list[str],
            cluster: str, 
            labels: dict = None, 
            pods: dict = None, 
            template: dict = None
        ) -> None:

        self.name = name.lower()
        self.cluster = cluster
        self.docid = f'_nd_node_k8sapp_{self.cluster}_{self.name.replace(".","_")}'
        self.domains = set(domains)
        self.labels = labels or {}
        self.pods = pods or {}
        self.template = template or {}

        self.type = 'Kubernetes App'
        self.psmlFooter = []

    @property
    def ips(self) -> list:
        return []

    @property
    def psmlPodTemplate(self) -> Tag:
        section = BeautifulSoup('<section id="template" title="Pod Template" />', features = 'xml')
        count = 0
        for container, template in self.template.items():
            frag = section.new_tag('properties-fragment', id=f'container_{str(count)}')
            frag.append(psml.property(
                name = 'container', title = 'Container Name', value = container
            ))
            frag.append(psml.property(
                name = 'image', title = 'Image ID', value = template['image']
            ))
            for volume, paths in self.template[container]['volumes'].items():
                frag.append(psml.property(
                    name = 'pvc', title = 'Persistent Volume Claim', value = volume
                ))
                frag.append(psml.property(
                    name = 'mount_path', title = 'Path in Container', value = paths['mount_path']
                ))
                frag.append(psml.property(
                    name = 'sub_path', title = 'Path in PVC', value = paths['sub_path']
                ))

            section.append(frag)
            count += 1
        return section
                
    @property
    def psmlRunningPods(self) -> Tag:
        section = BeautifulSoup('<section id="pods" title="Running Pods" />', features = 'xml')
        count = 0
        for pod in self.pods.values():
            frag = section.new_tag('properties-fragment', id=f'pod_{str(count)}')
            frag.append(psml.property(
                name = 'pod', title = 'Pod', value = pod['name']
            ))
            frag.append(psml.propertyXref(
                name = 'ipv4', title = 'Worker IP', docid = f'_nd_ip_{pod["workerIp"].replace(".","_")}'
            ))
            frag.append(psml.propertyXref(
                name = 'worker_node', title = 'Worker Node', docid = pod["workerNode"]
            ))
            frag.append(psml.propertyXref(
                name = 'rancher', title="Pod on Rancher", docid = pod['rancher']
            ))
            count += 1
        return section
    
    @property
    def psmlBody(self) -> Iterable[Tag]:
        return [self.psmlPodTemplate, self.psmlRunningPods]

    @property
    def network(self) -> Network:
        return self._network

    @network.setter
    def network(self, new_network: Network) -> None:
        self._network = new_network
        for domain in self.domains:
            if domain in self.network.domains:
                self.network.domains[domain].node = self

    def merge(self, *_) -> NotImplementedError:
        raise NotImplementedError

## Public plugin class

from plugins.kubernetes.refresh import runner
from plugins.kubernetes.webhooks import create_app


class Plugin(BasePlugin):
    name = 'kubernetes'
    stages = ['nodes', 'pre-write']
    xslt = 'plugins/kubernetes/nodes.xslt'
    workerApps: dict

    def __init__(self) -> None:
        super().__init__()
        self.workerApps = defaultdict(lambda: defaultdict(list))

    def init(self) -> None:
        """
        Some initialisation for the plugin to work correctly

        :meta private:
        """
        # Create output dir
        for dir in ('out', 'src'):
            if not os.path.exists(f'plugins/kubernetes/{dir}'):
                os.mkdir(f'plugins/kubernetes/{dir}')

        auth = utils.config()['plugins']['kubernetes']
        with open('plugins/kubernetes/src/kubeconfig', 'w') as stream:
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

    def runner(self, network: Network, stage: str) -> None:
        if stage == 'nodes':
            runner(network)
        else:
            for node in network.nodes:
                if node.type == 'Kubernetes App':
                    node: App
                    # set node attr on all domains
                    for domain in node.domains:
                        if domain in network and network.domains[domain].node is not node:
                            network.domains[domain].node.domains.remove(domain)
                            network.domains[domain].node = node
                    # gather all workers final docids
                    for pod in node.pods.values():
                        if pod['workerIp'] in network.ips and network.ips[pod['workerIp']].node is not None:
                            pod['workerNode'] = network.ips[pod['workerIp']].node.docid
                            self.workerApps[node.cluster][pod['workerNode']].append(node.docid)

            for cluster in self.workerApps:
                self.workerApps[cluster] = {k: self.workerApps[cluster][k] for k in sorted(self.workerApps[cluster])}
    
            # with open('plugins/kubernetes/src/workerApps.json', 'w') as stream:
            #     stream.write(json.dumps(self.workerApps, indent = 2, cls = JSONEncoder))
                
            utils.xslt(
                xsl = 'plugins/kubernetes/workerAppsMaker.xslt', 
                src = 'plugins/kubernetes/src/workerApps.xml', 
                out = 'plugins/kubernetes/workerApps.xslt'
            )
            utils.xslt(
                xsl = 'plugins/kubernetes/pub.xslt', 
                src = 'plugins/kubernetes/src/workerApps.xml', 
                out = 'out/k8spub.psml'
            )           

    def approved_node(self, uri: str) -> Response:
        summary = pageseeder.pfrag2dict(pageseeder.get_fragment(uri, 'summary'))
        if summary['type'] == 'Kubernetes App':
            # create_app(some args go here)
            pass

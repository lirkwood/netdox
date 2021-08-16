"""
Used to read and modify the deployments running on the configured clusters.
"""
from __future__ import annotations

import os
from collections import defaultdict
from typing import Iterable

import yaml
from bs4.element import Tag
from flask import Response
from kubernetes import config
from kubernetes.client import ApiClient

from netdox import pageseeder, psml, utils
from netdox.networkobjs import Network
from netdox.networkobjs.base import Node
from netdox.plugins import BasePlugin as BasePlugin

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


class App(Node):
    """
    Kubernetes app from a namespaced deployment
    """
    cluster: str
    """Cluster this app is running in"""
    labels: dict
    """Labels applied to the pods"""
    template: dict
    """Template pods are started from"""
    pods: dict
    """A dict of the pods running this app"""
    type: str = 'Kubernetes App'

    ## dunder methods

    def __init__(self, 
            network: Network,
            name: str, 
            domains: list[str],
            cluster: str, 
            labels: dict = None, 
            pods: dict = None, 
            template: dict = None
        ) -> None:

        super().__init__(
            network = network, 
            name = name,
            docid = f'_nd_node_k8sapp_{cluster}_{name.replace(".","_")}',
            identity = f'k8s_{cluster}_{name}',
            domains = domains,
            ips = []
        )
        
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
            frag = Tag(is_xml=True, name='properties-fragment', attrs={'id': f'container_{str(count)}'})
            frag.append(psml.newprop(
                name = 'container', title = 'Container Name', value = container
            ))
            frag.append(psml.newprop(
                name = 'image', title = 'Image ID', value = template['image']
            ))
            for volume, paths in self.template[container]['volumes'].items():
                frag.append(psml.newprop(
                    name = 'pvc', title = 'Persistent Volume Claim', value = volume
                ))
                frag.append(psml.newprop(
                    name = 'mount_path', title = 'Path in Container', value = paths['mount_path']
                ))
                frag.append(psml.newprop(
                    name = 'sub_path', title = 'Path in PVC', value = paths['sub_path']
                ))

            section.append(frag)
            count += 1
        return section
                
    @property
    def psmlRunningPods(self) -> Tag:
        section = Tag(is_xml=True, name='section', attrs={'id':'pods', 'title':'Running Pods'})
        count = 0
        for pod in self.pods.values():
            frag = Tag(is_xml=True, name='properties-fragment', attrs={'id': f'pod_{str(count)}'})
            frag.append(psml.newprop(
                name = 'pod', title = 'Pod', value = pod['name']
            ))
            frag.append(psml.newxrefprop(
                name = 'ipv4', title = 'Worker IP', ref = f'_nd_ip_{pod["workerIp"].replace(".","_")}'
            ))
            frag.append(psml.newxrefprop(
                name = 'worker_node', title = 'Worker Node', ref = pod["workerNode"]
            ))
            link = psml.newprop(name = 'rancher', title="Pod on Rancher")
            link.append(Tag(name='link', attrs={'href': pod['rancher']}))
            frag.append(link)

            section.append(frag)
            count += 1
        return section

## Public plugin class

from plugins.kubernetes.pub import genpub
from plugins.kubernetes.refresh import runner
from plugins.kubernetes.webhooks import create_app


class Plugin(BasePlugin):
    name = 'kubernetes'
    stages = ['nodes', 'pre-write']
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
            conf = utils.config()['plugins']['kubernetes']
            for node in network.nodes:
                if node.type == 'Kubernetes App':
                    node: App
                    # set node attr on all domains
                    for domain in list(node.domains):
                        if domain in network.domains and network.domains[domain].node is not node:
                            if set(network.domains[domain].node.ips) & set(conf[node.cluster]['proxies']):
                                network.domains[domain].node.domains.remove(domain)
                                network.domains[domain].node = node
                            else:
                                node.domains.remove(domain)
                    # gather all workers final docids
                    for pod in node.pods.values():
                        if pod['workerIp'] in network.ips and network.ips[pod['workerIp']].node is not None:
                            pod['workerNode'] = network.ips[pod['workerIp']].node.docid
                            self.workerApps[node.cluster][pod['workerNode']].append(node.docid)

            for cluster in self.workerApps:
                self.workerApps[cluster] = {k: self.workerApps[cluster][k] for k in sorted(self.workerApps[cluster])}
    
            genpub(self.workerApps)  

    def approved_node(self, uri: str) -> Response:
        summary = psml.pfrag2dict(pageseeder.get_fragment(uri, 'summary'))
        if summary['type'] == 'Kubernetes App':
            # create_app(some args go here)
            pass

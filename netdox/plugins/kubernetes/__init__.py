"""
Used to read and modify the deployments running on the configured clusters.
"""
from __future__ import annotations

import os
from typing import Iterable, Union

import pageseeder
import utils
import yaml
from flask import Response
from networkobjs import Network, Node
from plugins import Plugin as BasePlugin

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


## Plugin node classes

class App(Node):
    """
    Kubernetes app from a namespaced deployment
    """
    cluster: str
    labels: dict
    template: dict
    pods: dict

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
        self.docid = f'_nd_node_k8app_{self.cluster}_{self.name.replace(".","_")}'
        self.domains = set(domains)
        self.labels = labels or {}
        self.pods = pods or {}
        self.template = template or {}

        self.type = 'Kubernetes App'

    @property
    def network(self) -> Network:
        return self._network

    @network.setter
    def network(self, new_network: Network) -> None:
        self._network = new_network

    def merge(self, object: App) -> App:
        ## Deal with apps with duped names
        raise NotImplementedError


class Worker(Node):
    """
    Kubernetes worker node
    """
    cluster: str
    vm: str
    apps: list

    def __init__(self, 
            name: str, 
            private_ip: str, 
            cluster: str,
            vm: str = None,
            public_ips: Iterable[str] = None, 
            domains: Iterable[str] = None,
            ) -> None:
        super().__init__(name, private_ip, public_ips=public_ips, domains=domains, type='Kubernetes Worker')

        self.cluster = cluster
        self.docid = f'_nd_node_k8worker_{self.cluster}_{self.name.replace(".","_")}'
        self.vm = vm
        self.apps = []

    def merge(self, node: Union[Node, App]) -> None:
        if self.private_ip == node.private_ip:
            self.domains = self.domains.union(node.domains)
            if node.type == self.type:
                self.apps = list(set(self.apps + node.apps))
            elif node.type == 'default':
                self.location = self.location or node.location
        return self

## Public plugin class

from plugins.kubernetes.refresh import runner
from plugins.kubernetes.webhooks import create_app


class Plugin(BasePlugin):
    name = 'kubernetes'
    stage = 'nodes'

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
                    'cluster': {'server': f"{details['server']}/k8s/clusters/{details['clusterId']}"},
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

    def runner(self, network: Network) -> None:
        runner(network)

    def approved_node(self, uri: str) -> Response:
        summary = pageseeder.pfrag2dict(pageseeder.get_fragment(uri, 'summary'))
        if summary['type'] == 'Kubernetes App':
            # create_app(some args go here)
            pass
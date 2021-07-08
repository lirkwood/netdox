"""
Used to read and modify the deployments running on the configured clusters.
"""
from __future__ import annotations

import os

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


## Node subclasses

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
        self.docid = f'_nd_node_k8sapp_{self.cluster}_{self.name.replace(".","_")}'
        self.domains = set(domains)
        self.labels = labels or {}
        self.pods = pods or {}
        self.template = template or {}

        self.type = 'Kubernetes App'

    @property
    def ips(self) -> list:
        return []

    @property
    def network(self) -> Network:
        return self._network

    @network.setter
    def network(self, new_network: Network) -> None:
        self._network = new_network

    def merge(self, *_) -> NotImplementedError:
        raise NotImplementedError

## Public plugin class

from plugins.kubernetes.refresh import runner
from plugins.kubernetes.webhooks import create_app


class Plugin(BasePlugin):
    name = 'kubernetes'
    stages = ['nodes']
    xslt = 'plugins/kubernetes/nodes.xslt'

    def init(self) -> None:
        """
        Some initialisation for the plugin to work correctly

        :meta private:
        """
        # Create output dir
        for dir in ('out', 'src'):
            if not os.path.exists(f'plugins/kubernetes/{dir}'):
                os.mkdir(f'plugins/kubernetes/{dir}')

        utils.jsonForXslt('plugins/kubernetes/src/workerApps.xml', 'workerApps.json')

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

    def runner(self, network: Network, *_) -> None:
        runner(network)

    def approved_node(self, uri: str) -> Response:
        summary = pageseeder.pfrag2dict(pageseeder.get_fragment(uri, 'summary'))
        if summary['type'] == 'Kubernetes App':
            # create_app(some args go here)
            pass

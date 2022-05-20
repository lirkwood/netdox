"""
Used to read and modify the deployments running on the configured clusters.
"""
from __future__ import annotations

import logging
import os
from collections import defaultdict
from typing import cast

import yaml
from kubernetes import config
from kubernetes.client import ApiClient
from netdox import psml, utils
from netdox import Network
from netdox.app import LifecycleStage

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


## Plugin stuff

from netdox.plugins.k8s.objs import App
from netdox.plugins.k8s.pub import genpub
from netdox.plugins.k8s.refresh import runner


def init(_: Network) -> None:
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
        if node.type == App.type:
            appnode = cast(App, node)
            for path in appnode.paths:
                domainpaths[path.split('/')[0]].add(path)
                pathnodes[path] = appnode
    
    for domain, paths in domainpaths.items():
        ## Add a pfrag of paths relevant to each domain
        network.domains[domain].psmlFooter.insert(
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
    LifecycleStage.INIT: init,
    LifecycleStage.NODES: runner,
    LifecycleStage.FOOTERS: domainapps,
    LifecycleStage.WRITE: genpub
}

__nodes__ = [App]

__output__ = ['k8spub.psml']

__config__ = {
    "cluster_name": {
        "proxies": [''],
        "location": '',
        "host": '',
        "clusterId": '',
        "projectId": '',
        "token": ''
    }
}
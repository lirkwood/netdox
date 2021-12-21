"""
Used to detect PageSeeder based applications running in Kubernetes containers.
Depends on the k8s plugin.
"""
import json
import logging
from typing import Any

import requests
from netdox import Network, psml
from netdox.plugins.k8s import App

logger = logging.getLogger(__name__)

IMAGES = {
    'psberlioz-simple': 'Simple Site'
}

__depends__ = ['k8s']
# TODO teach nwman about this attribute

def footer(network: Network) -> None:
    for node in network.nodes:
        if isinstance(node, App):
            for count, (pod, info) in enumerate(get_pod_info(node).items()):
                pageseeders = []
                for instance in info['about']['pageseeders']:
                    ps_node = network.domains[instance['url']].node
                    if ps_node:
                        pageseeders.append(ps_node.docid)

                frag = psml.PropertiesFragment(f'psk8s_{count}', [
                    psml.Property('pod', pod, 'Pod')
                ])
                frag.append([
                    psml.Property(
                        'pageseeder', 
                        psml.XRef(docid = docid), 
                        'Backend PageSeeder'
                    ) for docid in pageseeders
                ])
                node.psmlFooter.append(frag)

def get_pod_info(node: App) -> dict[str, Any]:
    """
    Returns a dictionary of info about the app in each pod 
    with a container that is running a PageSeeder-app image.

    :param node: A k8sapp.
    :type node: App
    :return: Dictionary mapping pod name to some json returned by the api.
    :rtype: dict[str, Any]
    """
    pods = {}
    for pod, info in node.template.items():
        image = info['image'].split('/')[-1].split(':')[0]
        if image in IMAGES:
            for domain in node.domains:
                info_resp = requests.get(f'http://{domain}/api/info.json')
                if info_resp.ok:
                    pods[pod] = json.loads(info_resp.text)
                    break
    return pods
"""
Used to detect PageSeeder based applications running in Kubernetes containers.
Depends on the k8s plugin.
"""
import json
import logging
import warnings
from traceback import format_exc
from typing import Any

import requests
from netdox import Network, psml
from netdox.plugins.k8s import App

logger = logging.getLogger(__name__)

IMAGES = {
    'psberlioz-simple',
}

__depends__ = ['k8s']
# TODO teach nwman about this attribute

def footers(network: Network) -> None:
    for node in network.nodes:
        if isinstance(node, App):
            try:
                ps_docids: list[str] = []
                for response in get_pageseeder_info(node):
                    try:
                        for ps_info in response['about']['pageseeders']:
                            ps_node = network.find_dns(ps_info['url'])
                            if ps_node: ps_docids.append(ps_node.docid)
                    except KeyError:
                        pass

                if ps_docids:
                    logger.debug(node.name)
                    node.psmlFooter.append(psml.PropertiesFragment(f'psk8s', [
                        psml.Property(
                            'pageseeder', 
                            psml.XRef(docid = docid), 
                            'Backend PageSeeder'
                        ) for docid in ps_docids
                    ]))

            except Exception:
                logger.debug('Exception thrown while finding PageSeeder instances for '
                    + f'{node.name}:\n {format_exc()}')

def get_pageseeder_info(node: App) -> list[Any]:
    """
    Queries the App for information about it's related PageSeeder instances.

    :param node: A k8sapp.
    :type node: App
    :return: A list of successful API responses, as parsed JSON objects.
    :rtype: dict[str, Any]
    """
    responses = []
    images = {container.image.split('/')[-1].split(':')[0] 
        for container in node.template}

    if (images & IMAGES):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            for domain in node.domains:
                info_resp = requests.get(f'http://{domain}/api/info.json', verify = False)
                if info_resp.ok:
                    try:
                        data = json.loads(info_resp.text)
                        if data: responses.append(data)
                    except json.JSONDecodeError:
                        pass
    return responses

__stages__ = {
    'footers': footers
}

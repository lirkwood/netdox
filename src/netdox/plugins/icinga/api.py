"""
API Functions
*************

Provides functions for interacting with the Icinga API and a class for managing Netdox-generated monitors.
"""
import json
import logging
from collections import defaultdict

import requests

from netdox import utils

logger = logging.getLogger(__name__)

TEMPLATE_ATTR = 'icinga_template'

##############
# Primitives #
##############

def fetch(type: str, icinga_host: str) -> requests.Response:
    """
    Returns all instances of a given object type.

    :param type: The type of object to search for.
    :type type: str
    :param icinga_host: The domain name of the Icinga instance to query.
    :type icinga_host: str
    :raises ValueError: If *icinga_host* is not one of the configured values.
    :return: The JSON returned by the API.
    :rtype: dict
    """
    try:
        auth = utils.config('icinga')[icinga_host]
    except KeyError:
        raise ValueError(f'Unrecognised Icinga host: {icinga_host}')
    return requests.get(f'https://{icinga_host}:5665/v1/objects/{type}', 
        auth=(auth["username"], auth["password"]), verify=False)

def create(type: str, icinga_host: str, name: str, body: dict) -> requests.Response:
    """
    Creates an instance of the given type, described by *body*.

    :param type: The type of object to create.
    :type type: str
    :param icinga_host: The domain name of the Icinga instance to create on.
    :type icinga_host: str
    :param body: The dictionary describing the object to create.
    :type body: dict
    :raises ValueError: If *icinga_host* is not one of the configured values.
    :return: The JSON returned by the API.
    :rtype: dict
    """
    try:
        auth = utils.config('icinga')[icinga_host]
    except KeyError:
        raise ValueError(f'Unrecognised Icinga host: {icinga_host}')
    return requests.put(
        url = f'https://{icinga_host}:5665/v1/objects/{type}/{name}', 
        auth = (auth["username"], auth["password"]), 
        data = json.dumps(body), 
        headers = {
            'Accept': 'application/json'
        }, 
        verify = False
    )

#######################
# Composite functions #
#######################

def fetchMonitors(icinga_host: str) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    """
    Returns a dictionary mapping a unique address to its generated and manually created monitor objects.

    :param icinga_host: The FQDN / IPv4 of the Icinga instance to query.
    :type icinga_host: str
    :return: A 2-tuple of dicts of strings mapped to lists of dictionaries (monitor objects)
    :rtype: tuple[dict[str, list[dict]], dict[str, list[dict]]]
    """
    hosts = json.loads(fetch('hosts', icinga_host).text)
    services = json.loads(fetch('services', icinga_host).text)

    hostServices = {}
    for service in services['results']:
        host = service['attrs']['host_name']
        if host not in hostServices:
            hostServices[host] = []
        hostServices[host].append(service['name'].split('!')[-1])

    generated, manual = defaultdict(list), defaultdict(list)
    for host in hosts['results']:
        # first template is just host name
        host['attrs']['templates'].pop(0)

        # (group is generated) XNOR (group should be generated)
        if host['attrs']['groups'] == ['generated']:
            container = generated
        else:
            container = manual
        container[host['attrs']['address']].append({
            "icinga": icinga_host,
            "address": host['attrs']['address'],
            "templates": host['attrs']['templates'],
            "services": [host['attrs']['check_command']],
            "display": host['name']
        })
    return generated, manual


def createHost(address: str, template: str, icinga_host: str) -> dict:
    return create('hosts', icinga_host, address, {
        'templates': [template],
        'attrs': {
            'address': address
        } 
    })
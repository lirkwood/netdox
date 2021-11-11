"""
API Functions
*************

Provides functions for interacting with the Icinga API.
"""
import json
import logging
from collections import defaultdict
from typing import DefaultDict
import warnings

import requests
from netdox import utils

logger = logging.getLogger(__name__)

TEMPLATE_ATTR = 'icinga_template'

##############
# Primitives #
##############
# TODO add cert verification to primitive calls

def fetch(icinga_host: str, type: str) -> requests.Response:
    """
    Returns all instances of a given object type.

    :param icinga_host: The domain name of the Icinga instance to query.
    :type icinga_host: str
    :param type: The type of object to search for.
    :type type: str
    :raises ValueError: If *icinga_host* is not one of the configured values.
    :return: The response from the API
    :rtype: requests.Response
    """
    try:
        auth = utils.config('icinga')[icinga_host]
    except KeyError:
        raise ValueError(f'Unrecognised Icinga host: {icinga_host}')
    else:
        logger.debug(f'Fetching {type} from {icinga_host}')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            return requests.get(
                url = f'https://{icinga_host}:5665/v1/objects/{type}', 
                auth = (auth["username"], auth["password"]),
                verify = False
            )

def create(icinga_host: str, type: str, name: str, body: dict) -> requests.Response:
    """
    Creates an object of the given type, described by *body*.

    :param icinga_host: The domain name of the Icinga instance to create on.
    :type icinga_host: str
    :param type: The type of object to create.
    :type type: str
    :param name: The name of the object to create.
    :type name:
    :param body: The dictionary describing the object to create.
    :type body: dict
    :raises ValueError: If *icinga_host* is not one of the configured values.
    :return: The response from the API
    :rtype: requests.Response
    """
    try:
        auth = utils.config('icinga')[icinga_host]
    except KeyError:
        raise ValueError(f'Unrecognised Icinga host: {icinga_host}')
    else:
        logger.debug(f'Creating {type} \'{name}\' on {icinga_host}')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            return requests.put(
                url = f'https://{icinga_host}:5665/v1/objects/{type}/{name}', 
                auth = (auth["username"], auth["password"]), 
                data = json.dumps(body), 
                headers = {'Accept': 'application/json'},
                verify = False
            )

def update(icinga_host: str, type: str, name: str, body: dict) -> requests.Response:
    """
    Updates an existing object of the given type to the state described by *body*.

    :param icinga_host: The domain name of the Icinga instance to update on.
    :type icinga_host: str
    :param type: The type of object to update.
    :type type: str
    :param name: The name of the object to update.
    :type name:
    :param body: The dictionary describing the desired state of the object.
    :type body: dict
    :raises ValueError: If *icinga_host* is not one of the configured values.
    :return: The response from the API
    :rtype: requests.Response
    """
    try:
        auth = utils.config('icinga')[icinga_host]
    except KeyError:
        raise ValueError(f'Unrecognised Icinga host: {icinga_host}')
    else:
        logger.debug(f'Updating {type} \'{name}\' on {icinga_host}')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            return requests.post(
                url = f'https://{icinga_host}:5665/v1/objects/{type}/{name}', 
                auth = (auth["username"], auth["password"]), 
                data = json.dumps(body), 
                headers = {'Accept': 'application/json'},
                verify = False
            )

def delete(icinga_host: str, type: str, name: str, cascade: bool = False) -> requests.Response:
    """
    Deletes the object with the given name.

    :param icinga_host: The domain name of the Icinga instance to delete from.
    :type icinga_host: str
    :param type: The type of object to delete.
    :type type: str
    :param name: The name of the object to delete.
    :type name: str
    :param cascade: Whether or not to delete depending objects, defaults to False
    :type cascade: bool, optional
    :raises ValueError: If *icinga_host* is not one of the configured values.
    :return: The response from the API
    :rtype: requests.Response
    """
    try:
        auth = utils.config('icinga')[icinga_host]
    except KeyError:
        raise ValueError(f'Unrecognised Icinga host: {icinga_host}')
    else:
        logger.debug(f'Deleting {type} \'{name}\' on {icinga_host}')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            return requests.delete(
                url = f'https://{icinga_host}:5665/v1/objects/{type}/{name}',
                auth = (auth["username"], auth["password"]),
                data = json.dumps({'cascade': cascade}),
                headers = {'Accept': 'application/json'},
                verify = False
            )


def restart(icinga_host: str) -> requests.Response:
    """
    Restarts the specified Icinga instance.

    :param icinga_host: The domain name of the Icinga instance to restart.
    :type icinga_host: str
    :raises ValueError: If *icinga_host* is not one of the configured values.
    :return: The response from the API
    :rtype: requests.Response
    """
    try:
        auth = utils.config('icinga')[icinga_host]
    except KeyError:
        raise ValueError(f'Unrecognised Icinga host: {icinga_host}')
    else:
        logger.debug(f'Restarting {icinga_host}')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            return requests.post(
                url = f'https://{icinga_host}:5665/v1/actions/restart-process',
                auth = (auth["username"], auth["password"]),
                headers = {'Accept': 'application/json'},
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
    hosts = json.loads(fetch(icinga_host, 'hosts').text)
    services = json.loads(fetch(icinga_host, 'services').text)

    hostServices: DefaultDict[str, list[str]] = defaultdict(list)
    for service in services['results']:
        host = service['attrs']['host_name']
        if host not in hostServices:
            hostServices[host] = []
        hostServices[host].append(service['name'].split('!')[-1])

    generated: DefaultDict[str, list[dict]] = defaultdict(list)
    manual: DefaultDict[str, list[dict]] = defaultdict(list)
    for host in hosts['results']:
        # first template is just host name
        host['attrs']['templates'].pop(0)
        services = [host['attrs']['check_command']] + hostServices[host['attrs']['address']]

        # TODO make generated group configurable
        if host['attrs']['groups'] == ['generated']:
            container = generated
        else:
            container = manual
        container[host['attrs']['address']].append({
            "icinga": icinga_host,
            "address": host['attrs']['address'],
            "templates": host['attrs']['templates'],
            "services": services,
            "display": host['name']
        })
    return generated, manual


def createHost(icinga_host: str, address: str, template: str = 'generic-host') -> requests.Response:
    """
    Creates a host object.

    :param icinga_host: The domain name of the Icinga instance to create on.
    :type icinga_host: str
    :param address: The address of the host object.
    :type address: str
    :param template: The template to use for the object.
    :type template: str
    :return: The response from the API.
    :rtype: requests.Response
    """
    return create(icinga_host, 'hosts', address, {
        'templates': [template],
        'attrs': {
            'address': address,
            'groups': ['generated']
        }})

def updateHost(icinga_host: str, address: str, attrs: dict) -> requests.Response:
    """
    Updates one or more attributes of a host object.

    :param icinga_host: The domain name of the Icinga instance to update on.
    :type icinga_host: str
    :param address: The address of the host object.
    :type address: str
    :param attrs: A dict of attributes to set on the object.
    :type attrs: dict
    :return: The response from the API.
    :rtype: requests.Response
    """
    return update(icinga_host, 'hosts', address, attrs)

def updateHostTemplate(icinga_host: str, address: str, template: str = 'generic-host') -> requests.Response:
    """
    Delete a host object and recreate with *template* as the template.

    :param icinga_host: The domain name of the Icinga instance to update on.
    :type icinga_host: str
    :param address: The address of the host object.
    :type address: str
    :param template: The template to use for the object.
    :type template: str
    :return: The response from the API.
    :rtype: requests.Response
    """
    removeHost(icinga_host, address).raise_for_status()
    return createHost(icinga_host, address, template)

def removeHost(icinga_host: str, address: str) -> requests.Response:
    """
    Removes a host object.

    :param icinga_host: The domain name of the Icinga instance to update on.
    :type icinga_host: str
    :param address: The address of the host object.
    :type address: str
    :return: The response from the API.
    :rtype: requests.Response
    """
    return delete(icinga_host, 'hosts', address, True)

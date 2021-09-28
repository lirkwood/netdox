"""
Used to read and modify the VMs managed by Xen Orchestra
"""
from __future__ import annotations

import json
from json.decoder import JSONDecodeError
import logging
import os
import random
from functools import wraps
from typing import Iterable

import websockets
from bs4 import Tag

from netdox import pageseeder, psml, utils
from netdox.objs import DefaultNode, Network
from netdox.objs.nwobjs import IPv4Address

logging.getLogger('websockets').setLevel(logging.INFO)

##################################
# Generic websocket interactions #
##################################

async def call(method: str, params: dict = {}, notification: bool = False) -> dict:
    """
    Makes a call with some given method and params, returns a JSON object

    :param method: The method to use with the call
    :type method: str
    :param params: Some params to pass to the method, defaults to {}
    :type params: dict, optional
    :param notification: Whether or not to expect a response, True if no response expected, defaults to False
    :type notification: bool, optional
    :return: A dictionary containing the response sent by the websocket server.
    :rtype: dict
    """
    if notification:
        await websocket.send(json.dumps({
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }))
    else:
        id = f"netdox-{random.randint(0, 99)}"
        await websocket.send(json.dumps({
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": id
        }))
        return await reciever(id)


def authenticate(func):
    """
    Decorator used to establish a WSS connection before the function runs
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        global websocket
        async with websockets.connect(url, max_size=3000000) as websocket:
            if 'error' in await call('session.signInWithPassword', {'email': creds['username'], 'password': creds['password']}):
                raise RuntimeError(f'Failed to sign in with user {creds["username"]}')
            else:
                return await func(*args, **kwargs)
    return wrapper


global frames
frames = {}
async def reciever(id: int) -> dict:
    """
    Consumes responses sent by websocket server, returns the one with the specified ID.

    :param id: The ID of the message to return
    :type id: int
    :return: A dictionary containing a response from the websocket server.
    :rtype: dict
    """
    if id in frames:
        return frames[id]
    async for message in websocket:
        message = json.loads(message)
        if 'id'in message:
            if message['id'] == id:
                return message
            else:
                frames[message['id']] = message


################
# Plugin stuff #
################

from netdox.plugins.xenorchestra.vm import VirtualMachine
from netdox.plugins.xenorchestra.fetch import runner
from netdox.plugins.xenorchestra.write import genpub


def init() -> None:
    """
    Some initialisation for the plugin to work correctly

    :meta private:
    """
    global creds
    creds = utils.config('xenorchestra')
    global url
    url = f"wss://{creds['host']}/api/"
    if not os.path.exists(utils.APPDIR+ 'plugins/xenorchestra/src'):
        os.mkdir(utils.APPDIR+ 'plugins/xenorchestra/src')

global pubdict
pubdict = {}
def nodes(network: Network) -> None:
    global pubdict
    pubdict = runner(network)

def write(network: Network) -> None:
    genpub(network, pubdict)



__stages__ = {
    'nodes': nodes,
    'write': write
}

"""
This module contains the NetworkManager class.
"""
from __future__ import annotations

import importlib
import json
import logging
import pkgutil
from datetime import date, timedelta
from traceback import format_exc
from types import ModuleType
from typing import Callable
from collections import defaultdict

from bs4.element import Tag

import netdox.plugins
from netdox import pageseeder, utils
from netdox.objs.containers import Network

logger = logging.getLogger(__name__)

class NetworkManager:
    """
    Discovers plugins and uses them to populate a Network object.
    """
    network: Network
    """The network object this class should manage."""
    config: dict
    """Dictionary of config values for communicating with PageSeeder etc."""
    pluginmap: dict[str, set[ModuleType]]
    """Dictionary of stages and their plugins"""
    stale: dict[str, dict[date, str]]
    """Dictionary containing information about stale URIs and their expiry date."""

    def __init__(self) -> None:

        self.network = Network(domainroles = utils.roles())
        self.config = utils.config()
        
        self.pluginmap = {
            'any': set(),
            'dns': set(),
            'nat': set(),
            'nodes': set(),
            'footers': set(),
            'write': set(),
            'cleanup': set()
        }
        self.nodemap = {}
        self.stages = self.pluginmap.keys()

        self.stale = {}

        try:
            with open(utils.APPDIR+ 'cfg/plugins.json', 'r') as stream:
                self.enabled = json.load(stream)
        except Exception:
            logger.warning('Unable to load plugin configuration file. No plugins will run.')
            self.enabled = []
        
        self.loadPlugins(netdox.plugins)

        for plugin in self.enabled:
            if 'netdox.plugins.'+ plugin not in [module.__name__ for module in self.plugins]:
                logger.warning(f'Plugin \'{plugin}\' is enabled but was not found.')

    ## Plugin methods

    @property
    def plugins(self) -> set[ModuleType]:
        """
        A set of all plugins in the pluginmap
        """
        return self.pluginmap['any']

    def add(self, plugin: ModuleType) -> None:
        """
        Adds a plugin to the pluginmap

        :param plugin: An instantiated subclass of Plugin
        :type plugin: Plugin
        """
        self.plugins.add(plugin)

        if hasattr(plugin, 'node_types'):
            for node_type in plugin.__nodes__:
                self.nodemap[node_type] = plugin

        for stage in plugin.__stages__:
            self.pluginmap[stage].add(plugin)

    def loadPlugins(self, namespace: ModuleType) -> None:
        """
        Scans a namespace for valid python modules and imports them.

        :param dir: The namespace to scan for plugins
        :type dir: str
        :raises ImportError: If an Exception is raised during the call to ``importlib.import_module``
        """
        for plugin in pkgutil.iter_modules(namespace.__path__):
            if plugin.name in self.enabled:
                try:
                    self.add(importlib.import_module(namespace.__name__ +'.'+ plugin.name))
                except Exception:
                    raise ImportError(f'[ERROR][nwman] Failed to import {plugin}: \n{format_exc()}')

    def initPlugins(self) -> None:
        """
        Initialises all plugins in the pluginmap.
        """
        for plugin in self.plugins:
            if hasattr(plugin, 'init') and isinstance(plugin.init, Callable):
                plugin.init()

    def runPlugin(self, plugin: ModuleType, stage: str = 'none') -> None:
        """
        Runs the runner method of a plugin with a Network object and the current stage as arguments.

        :param plugin: The plugin module to run.
        :type plugin: ModuleType
        :param stage: The stage to run
        :type stage: str, optional
        """
        try:
            plugin.__stages__[stage](self.network)
        except Exception:
            logger.error(f'{plugin.__name__} threw an exception during stage {stage}: \n{format_exc()}')

    def runStage(self, stage: str) -> None:
        """
        Runs all the plugins in a given stage

        :param stage: The stage to check for plugins
        :type stage: str
        """
        logger.info(f'Starting stage: {stage}')
        for plugin in self.pluginmap[stage]:
            self.runPlugin(plugin, stage)

    ## Serialisation

    def loadNetworkDump(self, inpath: str = utils.APPDIR + 'src/network.bin', encrypted = True) -> None:
        """
        Loads an encrypted, pickled network object.

        :param inpath: The path to the binary network dump, defaults to 'src/network.bin'
        :type inpath: str, optional
        :param encrypted: Whether or not the dump was encrypted, defaults to True
        :type encrypted: bool, optional
        """
        self.network = Network.fromDump(inpath, encrypted)

    ## Sentencing

    def staleReport(self) -> None:
        """
        Sentences stale network objects and adds a section on stale documents to the network report.
        """
        for folder in ('domains', 'ips', 'nodes'):
            self.stale[folder] = pageseeder.sentenceStale(folder)

        section = Tag(is_xml = True, 
            name = 'section', 
            attrs = {
                'id': 'stale', 
                'title': 'Stale Documents'
        })

        plus_thirty = date.today() + timedelta(days = 30)

        combined = defaultdict(set)
        for expiryMap in self.stale.values():
            for expiry, uris in expiryMap.items():
                for uri in uris:
                    combined[expiry].add(uri)

        todayFrag = Tag(is_xml = True, name = 'fragment', attrs = {'id': 'stale_today'})
        heading = Tag(is_xml = True, name = 'heading', attrs = {'level': '3'})
        heading.string = 'Sentenced Today'
        todayFrag.append(heading)

        for expiry, uris in combined.items():
            if expiry >= plus_thirty:
                for uri in uris:
                    todayFrag.append(Tag(is_xml = True,
                        name = 'blockxref',
                        attrs = {
                            'frag': 'default',
                            'uriid': uri
                        }
                    ))
        section.insert(0, todayFrag)

        for type, stale in self.stale.items():
            frag = Tag(is_xml = True, name = 'fragment', attrs = {'id': 'stale_'+ type})
            for expiry, uris in sorted(stale.items()):
                heading = Tag(is_xml=True, name='heading', attrs={'level': '3'})
                heading.string = expiry.isoformat()
                frag.append(heading)
                for uri in uris:
                    if uri not in combined:
                        frag.append(Tag(is_xml = True,
                        name = 'blockxref',
                        attrs = {
                            'frag': 'default',
                            'uriid': uri
                        }
                    ))
            section.append(frag)
        self.network.report.append(section)
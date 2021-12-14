"""
This module contains the NetworkManager class.
"""
from __future__ import annotations

import importlib
import json
import logging
import os
import pkgutil
from collections import defaultdict
from datetime import date, timedelta
from traceback import format_exc
from types import ModuleType
from typing import Iterator, Union

from bs4.element import Tag
from netdox import pageseeder, utils
from netdox.config import NetworkConfig, update_template
from netdox.containers import Network
from netdox.helpers import LabelDict
from netdox.nodes import Node

logger = logging.getLogger(__name__)

class NetworkManager:
    """
    Discovers plugins and uses them to populate a Network object.
    """
    network: Network
    """The network object this class should manage."""
    namespace: ModuleType
    """The namespace package to load plugins from."""
    DEFAULT_NAMESPACE = 'netdox.plugins'
    """Name of the namespace package to load by default."""
    pluginmap: dict[str, set[ModuleType]]
    """Dictionary of stages and their plugins."""
    nodemap: dict[type[Node], ModuleType]
    """Maps the subclasses of Node that a plugin exports to the module object."""
    enabled: PluginWhitelist
    """List of plugins enabled by the user."""
    stale: dict[date, set[str]]
    """Dictionary mapping stale URIs to their expiry date."""

    def __init__(self, namespace: ModuleType = None, whitelist: list[str] = None, network: Network = None) -> None:
        """
        Constructor.

        :param namespace: Namespace to load plugins from, defaults to DEFAULT_NAMESPACE
        :type namespace: ModuleType, optional
        :param whitelist: List of plugin names to enable.
        If equal to PluginWhitelist.WILDCARD (["*"]), all plugins are enabled.
        If not set, defaults to the value in the config file. 
        If the file is missing or empty, falls back to wildcard.
        :type whitelist: list[str], optional
        :param network: existing Network object to use, defaults to None.
        :type network: Network, optional
        """
        # Initialisation
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

        self.stale = defaultdict(set)

        if whitelist:
            self.enabled = PluginWhitelist(whitelist)
        else:
            try:
                with open(utils.APPDIR+ 'cfg/plugins.json', 'r') as stream:
                    self.enabled = PluginWhitelist(json.load(stream))
            except FileNotFoundError:
                logger.warning('Plugin configuration file is missing from: ',
                    os.path.realpath(os.path.join(utils.APPDIR, 'cfg/plugins.json')))
                self.enabled = PluginWhitelist(PluginWhitelist.WILDCARD)
            except Exception:
                logger.warning('Unable to load plugin configuration file.')
                self.enabled = PluginWhitelist(PluginWhitelist.WILDCARD)
        
        self.namespace = namespace or importlib.import_module(self.DEFAULT_NAMESPACE)
        self.loadPlugins()

        # Reporting
        if self.enabled.is_wildcard:
            logger.warning('Plugin whitelist is wildcard. All plugins will be enabled.')
        else:
            for plugin in self.enabled:
                if f'{self.namespace.__name__}.{plugin}' not in [module.__name__ for module in self.plugins]:
                    logger.warning(f"Plugin '{plugin}' is enabled but was not found.")

        if self.plugins:
            logger.info(f"NetworkManager discovered the following plugins in '{self.namespace.__name__}': "
                + json.dumps([plugin.__name__.split('.')[-1] for plugin in self.plugins], indent = 2))
        else:
            logger.warning(f"Failed to discover any plugins in '{self.namespace.__name__}'")

        # Network
        self.network = network or Network(
            config = self.validConfig(), 
            labels = LabelDict.from_pageseeder()
        )

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

        for node_type in getattr(plugin, '__nodes__', []):
            self.nodemap[node_type] = plugin

        for stage in getattr(plugin, '__stages__', []):
            self.pluginmap[stage].add(plugin)

    def loadPlugins(self) -> None:
        """
        Scans a namespace for valid python modules and imports them.

        :param dir: The namespace to scan for plugins
        :type dir: str
        :raises ImportError: If an Exception is raised during the call to ``importlib.import_module``
        """
        for plugin in pkgutil.iter_modules(getattr(self.namespace, '__path__', ())):
            if plugin.name in self.enabled:
                try:
                    self.add(importlib.import_module(self.namespace.__name__ +'.'+ plugin.name))
                except Exception:
                    raise ImportError(f'Failed to import {plugin}: \n{format_exc()}')

    def initPlugins(self) -> None:
        """
        Initialises all plugins in the pluginmap.
        """
        for plugin in self.plugins:
            init = getattr(plugin, 'init', None)
            if callable(init):
                init()

    def runPlugin(self, plugin: ModuleType, stage: str) -> None:
        """
        Runs the runner method of a plugin with a Network object and the current stage as arguments.

        :param plugin: The plugin module to run.
        :type plugin: ModuleType
        :param stage: The stage to run
        :type stage: str, optional
        """
        stages = getattr(plugin, '__stages__', {stage: lambda _: ...})
        try:
            stages[stage](self.network)
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

    @property
    def pluginAttrs(self) -> set[str]:
        """
        Returns a set of label-configurable attributes provided by plugins.

        :return: A set of strings to be used as property names in the config.
        :rtype: set[str]
        """
        return {
            attr for plugin in {
                plugin for plugin in self.plugins
            } for attr in getattr(plugin, '__attrs__', ())
        }

    def validConfig(self) -> NetworkConfig:
        """
        Fetches the config from PageSeeder, but performs some validation
        before returning it.

        If the config has incorrect attributes specified for a label,
        the template will be updated, and a valid config created.
        This config will be serialised for the upload.
        """
        cfg = NetworkConfig.from_pageseeder()
        # TODO find solution for config vals being dropped when the plugin is disabled
        if cfg.is_empty or (not cfg.normal_attrs) or (self.pluginAttrs - cfg.attrs):
            logger.warning('Updating config template on PageSeeder.')
            update_template(self.pluginAttrs)
            cfg.update_attrs(self.pluginAttrs)
            with open(utils.APPDIR+ 'out/config.psml', 'w') as stream:
                stream.write(cfg.to_psml())
        return cfg

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
            for expiry, uri_list in pageseeder.sentenceStale(folder).items():
                self.stale[expiry] |= set(uri_list)

        section = Tag(is_xml = True, 
            name = 'section', 
            attrs = {
                'id': 'stale', 
                'title': 'Stale Documents'
        })

        plus_thirty = date.today() + timedelta(days = 30)

        if plus_thirty in self.stale:
            todayFrag = Tag(is_xml = True, name = 'fragment', attrs = {'id': plus_thirty.isoformat()})
            heading = Tag(is_xml = True, name = 'heading', attrs = {'level': '2'})
            heading.string = 'Sentenced Today'
            todayFrag.append(heading)

            for uri in self.stale.pop(plus_thirty):
                todayFrag.append(Tag(is_xml = True,
                    name = 'blockxref',
                    attrs = {
                        'frag': 'default',
                        'uriid': uri
                    }
                ))
            section.insert(0, todayFrag)

        for expiry, uris in sorted(self.stale.items(), reverse = True):
            frag = Tag(is_xml = True, name = 'fragment', attrs = {'id': expiry.isoformat()})
            heading = Tag(is_xml=True, name='heading', attrs={'level': '2'})
            heading.string = 'Expiring on: '+ expiry.isoformat()
            frag.append(heading)
            for uri in uris:
                frag.append(Tag(is_xml = True,
                    name = 'blockxref',
                    attrs = {
                        'frag': 'default',
                        'uriid': uri
                    }
                ))
            section.append(frag)
        self.network.report.addSection(str(section))

class PluginWhitelist(list):
    WILDCARD = ["*"]
    """Constant that matches every plugin."""
    @property
    def is_wildcard(self) -> bool:
        return self == self.WILDCARD

    def __contains__(self, key) -> bool:
        if self.is_wildcard:
            return True
        return super().__contains__(key)

    def __iter__(self) -> Iterator[str]:
        if self.is_wildcard:
            return ().__iter__()
        return super().__iter__()
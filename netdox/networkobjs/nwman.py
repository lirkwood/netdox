import importlib
import json
import os
import utils
from collections import defaultdict
from traceback import format_exc
from typing import Iterator, ValuesView

from plugins import BasePlugin

from .containers import Network

class NetworkManager:
    """
    Discovers plugins and uses them to populate a Network object.
    """
    network: Network
    """The network object this class should manage."""
    plugins: set
    """Set of plugins loaded by the networkmaanager."""

    def __init__(self) -> None:

        self.network = Network()
        self.config = utils.config()

        
        self.pluginmap = defaultdict(dict)
        self.pluginmap = {
            'all':{},
            'dns': {},
            'nodes': {},
            'pre-write': {},
            'post-write': {}
        }
        self.stages = self.pluginmap.keys()

        try:
            with open('src/plugins.json', 'r') as stream:
                self.enabled = json.load(stream)
        except Exception:
            print('[WARNING][plugins] Unable to load plugin configuration file. No plugins will run.')
            self.enabled = []
        
        self.loadPlugins('plugins')

    def __iter__(self) -> Iterator[BasePlugin]:
        yield from self.plugins.values()
    
    def __getitem__(self, key: str) -> BasePlugin:
        """
        Returns a plugin by name.
        """
        return self.plugins[key]

    def __contains__(self, key: str) -> bool:
        """
        Tests if a plugin with the given name has been loaded
        """
        return self.plugins.__contains__(key)

    @property
    def plugins(self) -> dict[str, BasePlugin]:
        """
        A dictionary of all plugins in the pluginmap
        """
        return self.pluginmap['all']

    @property
    def nodes(self) -> ValuesView[BasePlugin]:
        return self.pluginmap['nodes'].values()

    @property
    def dns(self) -> ValuesView[BasePlugin]:
        return self.pluginmap['dns'].values()

    @property
    def pre(self) -> ValuesView[BasePlugin]:
        return self.pluginmap['pre-write'].values()

    @property
    def post(self) -> ValuesView[BasePlugin]:
        return self.pluginmap['post-write'].values()

    def add(self, plugin: BasePlugin) -> None:
        """
        Adds a plugin to the PluginManager

        :param plugin: An instantiated subclass of Plugin
        :type plugin: Plugin
        """
        self.plugins[plugin.name] = plugin

        if hasattr(plugin, 'node_types'):
            for node_type in plugin.node_types:
                self.nodemap[node_type] = plugin

        for stage in plugin.stages:
            self.pluginmap[stage][plugin.name] = plugin

    def loadPlugins(self, dir: str) -> None:
        """
        Scans a directory for valid python modules and imports them.

        :param dir: The directory to scan for plugins
        :type dir: str
        :raises ImportError: If an Exception is raised during the call to ``importlib.import_module``
        """
        for plugindir in os.scandir(dir):
            if plugindir.is_dir() and plugindir.name != '__pycache__':
                pluginName = plugindir.name
                if pluginName in self.enabled:
                    try:
                        plugin = importlib.import_module(f'plugins.{pluginName}')
                    except Exception:
                        raise ImportError(f'[ERROR][plugins] Failed to import {pluginName}: \n{format_exc()}')
                    else:
                        if hasattr(plugin, 'Plugin'):
                            self.add(plugin.Plugin())

    def initPlugin(self, plugin_name: str) -> None:
        self.plugins[plugin_name].init()

    def initStage(self, stage: str) -> None:
        for plugin in self.pluginmap[stage].values():
            plugin.init()

    def initPlugins(self) -> None:
        for plugin in self:
            plugin.init()

    def runPlugin(self, name: str = None, plugin: BasePlugin = None, stage: str = 'none') -> None:
        """
        Runs the runner method of a plugin with a Network object and the current stage as arguments.

        :param name: The name of a plugin already loaded by the PluginManager. Must be provided if ``plugin`` is not. Defaults to None
        :type name: str, optional
        :param plugin: An instance of Plugin or a class that inherits from it. Must be provided if ``name`` is not. Defaults to None
        :type plugin: Plugin, optional
        :param stage: The current stage to pass to the runner method, defaults to 'none'
        :type stage: str, optional
        :raises RuntimeError: If both name and plugin take Falsy values
        """        
        if not name and not plugin:
            raise RuntimeError('Must provide one of: plugin name, plugin')
        elif not plugin:
            plugin = self[name]
        
        try:
            plugin.runner(self.network, stage)
        except Exception:
            print(f'[ERROR][plugins] {plugin.name} threw an exception: \n{format_exc()}')

    def runStage(self, stage: str) -> None:
        """
        Runs all the plugins in a given stage

        :param stage: The stage to check for plugins
        :type stage: str
        """
        print(f'[INFO][plugins] Starting stage: {stage}')
        for pluginName, plugin in self.pluginmap[stage].items():
            self.runPlugin(pluginName, plugin, self.network, stage)
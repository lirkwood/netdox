"""
The pluginmanager class initialises and exposes plugins as imported modules for use by Netdox and other plugins.

When a plugin is loaded it's *init* method is called if present and it is import via importlib.import_module()

Initially the default plugins were baked in features, but it became obvious that in order for Netdox to be useful anywhere outside of an internal context, it needed completely modular inputs at least.
This was quickly expanded to allow custom code to be executed at multiple points of interest, which became the plugin stages.
"""

import importlib
import os
from abc import ABC, abstractmethod
from collections import defaultdict
from traceback import format_exc
from types import ModuleType
from typing import Iterator, KeysView

from networkobjs import Network


class Plugin(ABC):
    """
    Base class for plugins
    """
    name: str
    stage: str
    node_types: list[str]

    @abstractmethod
    def init(self) -> None:
        """
        Any initialisation that should be done before the runner is called.
        """
        pass

    @abstractmethod
    def runner(self, network: Network) -> None:
        """
        The main function of the plugin.
        """
        pass


class PluginManager:
    """
    Used to find, import, and run plugins.
    """
    pluginmap: defaultdict[dict[str, Plugin]]
    nodemap: dict[str, Plugin]
    stages: KeysView[str]

    def __init__(self) -> None:
        self.pluginmap = defaultdict(dict)
        self.pluginmap = {
            'all':{},
            'dns': {},
            'nodes': {},
            'pre-write': {},
            'post-write': {}
        }
        self.stages = self.pluginmap.keys()
        self.loadPlugins('plugins')

    def __iter__(self) -> Iterator[Plugin]:
        yield from self.plugins.values()
    
    def __getitem__(self, key: str) -> Plugin:
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
    def plugins(self) -> dict:
        """
        A dictionary of all plugins in the pluginmap
        """
        return self.pluginmap['all']

    def add(self, plugin: Plugin) -> None:
        """
        Adds a plugin to the pluginmap.

        :Args:
            plugin:
                An instance of the Plugin abstract base class
        """
        self.plugins[plugin.name] = plugin
        for node_type in plugin.node_types:
            self.nodemap[node_type] = plugin
        if plugin.stage:
            self.pluginmap[plugin.stage][plugin.name] = plugin
    
    def loadPlugins(self, dir: str) -> None:
        """
        Scans a directory for valid python modules and imports them.
        """
        for plugindir in os.scandir(dir):
            if plugindir.is_dir() and plugindir.name != '__pycache__':
                pluginName = plugindir.name
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
        for plugin in self.pluginmap[stage]:
            plugin.init()

    def initPlugins(self) -> None:
        for plugin in self:
            plugin.init()

    def runPlugin(self, name: str = '', plugin: ModuleType = None, network: Network = None) -> None:
        """
        Runs the *runner* function from a given plugin with forward and reverse dns as arguments

        :Args:
            name: str
                The name of a loaded plugin to call *runner* from
            plugin: ModuleType
                The module object of the plugin to call *runner* from
            forward_dns:
                A forward DNS set
            reverse_dns:
                A reverse DNS set
        """
        if not name and not plugin:
            raise RuntimeError('Must provide one of: plugin name, plugin')
        elif not plugin:
            plugin = self[name]

        network = network or Network()
        
        try:
            plugin.runner(network)
        except Exception:
            print(f'[ERROR][pluginmanager] {plugin.__name__} threw an exception: \n{format_exc()}')

    def runStage(self, stage: str, network: Network) -> None:
        """
        Runs all the plugins in a stage

        :Args:
            stage: str
                The stage of plugins to call *runner* on
            forward_dns:
                A forward DNS set
            reverse_dns:
                A reverse DNS set
        """
        if stage not in self.pluginmap:
            raise ValueError(f'Unknown stage: {stage}')

        print(f'[INFO][pluginmanager] Starting stage: {stage}')
        for pluginName, plugin in self.pluginmap[stage].items():
            self.runPlugin(pluginName, plugin, network)

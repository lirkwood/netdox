"""
The pluginmaster class initialises and exposes plugins as imported modules for use by Netdox and other plugins.

Initially the default plugins were baked in features, but it became obvious that in order for Netdox to be useful anywhere outside of an internal context, it needed completely modular inputs at least.
This was quickly expanded to allow custom code to be executed at multiple points of interest, which became the plugin stages.
This script may also be used to manually run a plugin or plugin stage. 
Usage: ``python3 pluginmaster.py <plugin|stage> <name>``
"""

from traceback import format_exc
from types import ModuleType
from typing import KeysView
import importlib, os


class pluginmanager:
    pluginmap: dict[str, dict[str, ModuleType]]
    stages: KeysView[str]

    def __init__(self) -> None:
        self.pluginmap = {
            'all':{},
            'dns': {},
            'resources': {},
            'pre-write': {},
            'post-write': {},
            'none': {}
        }
        self.stages = self.pluginmap.keys()
        self.loadPlugins('plugins')
    
    def __getitem__(self, key) -> ModuleType:
        """
        Returns a plugin by name.

        :Returns:
            The module object of the specified plugin
        """
        return self.pluginmap['all'][key]

    def add(self, name: str, module: ModuleType, stage: str = 'none') -> None:
        """
        Adds a plugin to the pluginmap.

        :Args:
            name: str
                The name of the plugin to add
            module: ModuleType
                The module object to add as the plugin
            stage: str
                The stage at which to call *runner* for this plugin ('none' to never call)
        """
        self.pluginmap[stage][name] = module
        self.pluginmap['all'][name] = module
    
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
                    if hasattr(plugin, 'stage'):
                        stage = plugin.stage.lower()
                    else:
                        stage = 'none'
                    self.add(pluginName, plugin, stage)
    

    def runPlugin(self, name: str = '', plugin: ModuleType = None, forward_dns: dict = {}, reverse_dns: dict = {}) -> None:
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
        
        try:
            plugin.runner(forward_dns, reverse_dns)
        except Exception:
            print(f'[ERROR][pluginmaster] {plugin.__name__} threw an exception: \n{format_exc()}')

    def runStage(self, stage: str, forward_dns: dict = {}, reverse_dns: dict = {}) -> None:
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

        for pluginName, plugin in self.pluginmap[stage].items():
            self.runPlugin(pluginName, plugin, forward_dns, reverse_dns)
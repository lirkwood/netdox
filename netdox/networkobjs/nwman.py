import importlib
import json
import os
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from traceback import format_exc

import pageseeder
import utils
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
    stale_pattern: re.Pattern = re.compile(r'expires-(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})')

    def __init__(self) -> None:

        self.network = Network(domainroles = utils.roles())
        self.config = utils.config()
        
        self.pluginmap = defaultdict(dict)
        self.pluginmap = {
            'all':{},
            'dns': {},
            'nat': {},
            'nodes': {},
            'pre-write': {},
            'post-write': {}
        }
        self.nodemap = {}
        self.stages = self.pluginmap.keys()

        try:
            with open('src/plugins.json', 'r') as stream:
                self.enabled = json.load(stream)
        except Exception:
            print('[WARNING][nwman] Unable to load plugin configuration file. No plugins will run.')
            self.enabled = []
        
        self.loadPlugins('plugins')

    @property
    def plugins(self) -> dict[str, BasePlugin]:
        """
        A dictionary of all plugins in the pluginmap
        """
        return self.pluginmap['all']

    def add(self, plugin: BasePlugin) -> None:
        """
        Adds a plugin to the pluginmap

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
                        raise ImportError(f'[ERROR][nwman] Failed to import {pluginName}: \n{format_exc()}')
                    else:
                        if hasattr(plugin, 'Plugin'):
                            self.add(plugin.Plugin())

    def initPlugin(self, plugin_name: str) -> None:
        """
        Calls the *init* method on the plugin with name *plugin_name*.

        :param plugin_name: The name of the plugin to initialise
        :type plugin_name: str
        """
        self.plugins[plugin_name].init()

    def initStage(self, stage: str) -> None:
        """
        Initialises all plugins in *stage*.

        :param stage: The stage to initialise.
        :type stage: str
        """
        for plugin in self.pluginmap[stage].values():
            plugin.init()

    def initPlugins(self) -> None:
        """
        Initialises all plugins in the pluginmap.
        """
        for plugin in self.plugins.values():
            plugin.init()

    def runPlugin(self, name: str = None, plugin: BasePlugin = None, stage: str = 'none') -> None:
        """
        Runs the runner method of a plugin with a Network object and the current stage as arguments.

        :param name: The name of a plugin already loaded by the NetworkManager. Must be provided if ``plugin`` is not. Defaults to None
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
            plugin = self.plugins[name]
        
        try:
            plugin.runner(self.network, stage)
        except Exception:
            print(f'[ERROR][nwman] {plugin.name} threw an exception: \n{format_exc()}')

    def runStage(self, stage: str) -> None:
        """
        Runs all the plugins in a given stage

        :param stage: The stage to check for plugins
        :type stage: str
        """
        print(f'[INFO][nwman] Starting stage: {stage}')
        for pluginName, plugin in self.pluginmap[stage].items():
            self.runPlugin(pluginName, plugin, stage)

    def sentenceStale(self, dir: str) -> None:
        """
        Adds stale labels to any files present in *dir* on PageSeeder, but not locally.

        :param dir: The directory, relative to `website/` on PS or `out/` locally.
        :type dir: str
        :return: A list of stale URIs.
        :rtype: list
        """
        today = datetime.now().date()
        group_path = f"/ps/{utils.config()['pageseeder']['group'].replace('-','/')}"
        stale = []
        if dir in pageseeder.urimap():
            local = utils.fileFetchRecursive(os.path.join('out', dir))

            remote = json.loads(pageseeder.get_uris(pageseeder.urimap()[dir], params={
                'type': 'document',
                'relationship': 'descendants'
            }))

            for file in remote["uris"]:
                commonpath = file["decodedpath"].split(f"{group_path}/website/")[-1]
                uri = file["id"]
                if 'labels' in file: 
                    labels = ','.join(file['labels'])
                    marked_stale = re.search(self.stale_pattern, labels)
                else:
                    labels = ''
                    marked_stale = False

                expiry = date.fromisoformat(marked_stale['date']) if marked_stale else None
                
                if os.path.normpath(os.path.join('out', commonpath)) not in local:
                    if marked_stale:
                        if expiry <= today:
                            pageseeder.archive(uri)
                        else:
                            stale[uri] = marked_stale['date']
                    else:
                        plus_thirty = today + timedelta(days = 30)
                        if labels: labels += ','
                        labels += f'stale,expires-{plus_thirty}'
                        pageseeder.patch_uri(uri, {'labels':labels})
                        print(f'[INFO][nwman] File {commonpath} is stale and has been sentenced.')
                        stale[uri] = str(plus_thirty)
                # if marked stale but exists locally
                else:
                    if marked_stale:
                        labels = re.sub(self.stale_pattern, '', labels) # remove expiry label
                        labels = re.sub(r',,',',', labels) # remove double commas
                        labels = re.sub(r',$','', labels) # remove trailing commas
                        labels = re.sub(r'^,','', labels) # remove leading commas
                        pageseeder.patch_uri(uri, {'labels':labels})

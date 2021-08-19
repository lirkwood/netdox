from __future__ import annotations

import importlib
import json
import os
import pickle
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from traceback import format_exc
from types import ModuleType
from typing import Callable, Type
import pkgutil

from netdox import pageseeder, utils
from netdox.crypto import Cryptor
from netdox.objs.containers import Network
import netdox.plugins


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
    stale_pattern: re.Pattern = re.compile(r'expires-(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})')

    def __init__(self) -> None:

        self.network = Network(domainroles = utils.roles())
        self.config = utils.config()
        
        self.pluginmap = {
            'any': set(),
            'dns': set(),
            'nodes': set(),
            'nat': set(),
            'footers': set(),
            'write': set(),
            'cleanup': set()
        }
        self.nodemap = {}
        self.stages = self.pluginmap.keys()

        try:
            with open(utils.APPDIR+ 'src/plugins.json', 'r') as stream:
                self.enabled = json.load(stream)
        except Exception:
            print('[WARNING][nwman] Unable to load plugin configuration file. No plugins will run.')
            self.enabled = []
        
        self.loadPlugins(netdox.plugins)

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
            print(f'[ERROR][nwman] {plugin.__name__} threw an exception during stage {stage}: \n{format_exc()}')

    def runStage(self, stage: str) -> None:
        """
        Runs all the plugins in a given stage

        :param stage: The stage to check for plugins
        :type stage: str
        """
        print(f'[INFO][nwman] Starting stage: {stage}')
        for plugin in self.pluginmap[stage]:
            self.runPlugin(plugin, stage)

    ## Cleanup

    def sentenceStale(self, dir: str) -> dict[str, str]:
        """
        Adds stale labels to any files present in *dir* on PageSeeder, but not locally.

        :param dir: The directory, relative to `website/` on PS or `out/` locally.
        :type dir: str
        :return: A dict of stale URIs, mapped to their expiry date.
        :rtype: dict[str, str]
        """
        today = datetime.now().date()
        group_path = f"/ps/{utils.config()['pageseeder']['group'].replace('-','/')}"
        stale = {}
        if dir in pageseeder.urimap():
            local = utils.fileFetchRecursive(
                os.path.normpath(os.path.join(utils.APPDIR, 'out', dir)),
                relative = utils.APPDIR + 'out'
            )

            remote = json.loads(pageseeder.get_uris(pageseeder.urimap()[dir], params={
                'type': 'document',
                'relationship': 'descendants'
            }))

            for file in remote["uris"]:
                commonpath = os.path.normpath(file["decodedpath"].split(f"{group_path}/website/")[-1])
                uri = file["id"]
                if 'labels' in file: 
                    labels = ','.join(file['labels'])
                    marked_stale = re.search(self.stale_pattern, labels)
                else:
                    labels = ''
                    marked_stale = False

                expiry = date.fromisoformat(marked_stale['date']) if marked_stale else None
                
                if commonpath not in local:
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
        return stale

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
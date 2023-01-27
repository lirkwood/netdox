from __future__ import annotations

import importlib
import json
import logging
import os
import pkgutil
from enum import Enum
import shutil
from traceback import format_exc
from types import ModuleType
from typing import Callable, Iterator, Optional, Type
from zipfile import ZipFile

from netdox import config, containers, utils
from netdox.helpers import Counter, LabelDict, Report
from netdox.nodes import Node
from netdox import pageseeder

logger = logging.getLogger(__name__)

## Plugins

class PluginManager:
    """
    Discovers plugins.
    """
    namespace: ModuleType
    """The namespace package to load plugins from."""
    DEFAULT_NAMESPACE = 'netdox.plugins'
    """Name of the namespace package to load by default."""
    plugins: set[Plugin]
    """Set of loaded plugins."""
    loaded: list[str]
    """List of the names of loaded plugins."""
    nodemap: dict[type[Node], Plugin]
    """Maps the subclasses of Node that a plugin exports to the module object."""
    enabled: PluginWhitelist
    """List of plugins enabled by the user."""

    def __init__(self, 
            namespace:Optional[ModuleType] = None, 
            whitelist: Optional[list[str]] = None
        ) -> None:
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
        self.plugins = set()
        self.loaded = []
        self.nodemap = {}
        self.enabled = PluginWhitelist(whitelist) if whitelist else self._load_whitelist()
        self.namespace = namespace or importlib.import_module(self.DEFAULT_NAMESPACE)
        self.loadPlugins()

        # Reporting
        if self.enabled.is_wildcard:
            logger.warning('Plugin whitelist is wildcard. All plugins will be enabled.')
        else:
            for plugin in self.enabled:
                if plugin not in [_plugin.name for _plugin in self.plugins]:
                    logger.warning(f"Plugin '{plugin}' is enabled but was not found.")

        if self.plugins:
            logger.info(f"NetworkManager discovered the following plugins in '{self.namespace.__name__}': "
                + json.dumps([plugin.name for plugin in self.plugins], indent = 2))
        else:
            logger.warning(f"Failed to discover any plugins in '{self.namespace.__name__}'")

    ## Plugin methods

    def add(self, plugin: Plugin) -> None:
        """
        Adds a plugin to the pluginmap

        :param plugin: An instantiated subclass of Plugin
        :type plugin: Plugin
        """
        self.plugins.add(plugin)

        for node_type in plugin.node_types:
            self.nodemap[node_type] = plugin

    def loadPlugins(self) -> None:
        """
        Scans a namespace for valid python modules and imports them.

        :param dir: The namespace to scan for plugins
        :type dir: str
        :raises ImportError: If an Exception is raised during the call to 
        ``importlib.import_module``
        """
        modules = list(pkgutil.iter_modules(getattr(self.namespace, '__path__', ())))
        for module in modules:
            logger.debug(f'Discovered module {module.name}')
            if (module.name in self.enabled and 
                module.name not in self.loaded):
                self._loadPlugin(module.name)

    def _loadPlugin(self, name: str) -> bool:
        """
        Loads a plugin from it's name.

        :param name: Name of the plugin to load.
        :type name: str
        :return: 
        :rtype: bool
        """
        try:
            plugin = Plugin(importlib.import_module(
                self.namespace.__name__ +'.'+ name))

            if not self.validate_deps(plugin):
                raise ImportError(
                    f'Failed to load dependecies for {plugin.name}')

            self.add(plugin)
            return True

        except Exception:
            logger.error(
                f'Failed to import {name}:\n{format_exc()}')
        return False

    def validate_deps(self, plugin: Plugin) -> bool:
        """
        Returns True if all of the dependencies for *plugin* are present in *names*.
        False otherwise.

        :param plugin: The plugin to validate the dependencies of.
        :type plugin: Plugin
        :param names: A list of names of available plugins.
        :return: True if plugin can run, else False.
        :rtype: bool
        """
        failed = set()
        for dep in plugin.dependencies:
            if dep not in self.enabled and dep not in self.loaded:
                if not self._loadPlugin(dep):
                    failed.add(dep)
        return not bool(failed)

    def initPlugins(self) -> None:
        """
        Initialises all plugins in the pluginmap.
        """
        for plugin in self.plugins:
            try:
                plugin.init()
            except Exception:
                logger.error(
                    f'{plugin.name} threw an exception during initialisation: \n{format_exc()}')

    def runPlugin(self, 
            network: containers.Network, 
            plugin: Plugin, 
            stage: LifecycleStage
        ) -> None:
        """
        Runs the registered method of *plugin* for *stage*.

        :param network: The Network object to populate.
        :type network: containers.Network
        :param plugin: The plugin module to run.
        :type plugin: ModuleType
        :param stage: The current stage.
        :type stage: LifecycleStage, optional
        """
        try:
            logger.debug(f'Running plugin {plugin.name} stage {stage.name}')
            plugin.stages[stage](network)
        except Exception:
            logger.error(f'{plugin.name} threw an exception during stage {stage.name}: \n{format_exc()}')

    def runStage(self, network: containers.Network, stage: LifecycleStage) -> None:
        """
        Runs all the plugins in a given stage

        :param network: The Network object to populate.
        :type network: containers.Network
        :param stage: The stage to check for plugins
        :type stage: LifecycleStage
        """
        logger.info(f'Starting stage: {stage.name}')
        for plugin in self.plugins:
            if stage in plugin.stages:
                self.runPlugin(network, plugin, stage)

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

    @property
    def output(self) -> set[str]:
        """
        Returns a set of the names of files and directories the running plugins will output to.
        """
        return { file for plugin in self.plugins for file in plugin.output }

    @property
    def nodes(self) -> set[Type[Node]]:
        """
        Returns a set of the types of all the Node subclasses exported by the running plugins.
        """
        return { node for plugin in self.plugins for node in plugin.node_types }

    def _load_whitelist(self) -> PluginWhitelist:
        """
        Returns a PluginWhitelist from the config file or a wildcard.

        :return: A PluginWhitelist instance.
        :rtype: PluginWhitelist
        """
        try:
            with open(utils.APPDIR+ 'cfg/plugins.json', 'r') as stream:
                return PluginWhitelist(json.load(stream))
        except FileNotFoundError:
            logger.warning('Plugin configuration file is missing from: ' +
                os.path.realpath(os.path.join(utils.APPDIR, 'cfg/plugins.json')))
            return PluginWhitelist(PluginWhitelist.WILDCARD)
        except Exception:
            logger.warning('Unable to load plugin configuration file.')
            return PluginWhitelist(PluginWhitelist.WILDCARD)

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


class Plugin:
    module: ModuleType
    """The imported plugin module object."""
    name: str
    """Name of this plugin."""
    stages: dict[LifecycleStage, Callable[[containers.Network], None]]
    """A dict mapping stages to a callable accepting a Network."""
    config: Optional[dict]
    """A dictionary of configuration values for this plugin.
    Will be used in the config template."""
    dependencies: set[str]
    """A set of plugin names this plugin depends on."""
    node_types: list[Type[Node]]
    """A list of the Node subclasses that this plugin exports."""
    output: set[str]
    """A set of the files and directory names this plugin writes output to."""

    def __init__(self, module: ModuleType) -> None:
        self.module = module
        self.name = module.__name__.split('.')[-1]
        self.stages = getattr(module, '__stages__')
        self.config = getattr(module, '__config__', None)
        self.dependencies = set(getattr(module, '__depends__', set()))
        self.node_types = list(getattr(module, '__nodes__', []))
        self.output = set(getattr(module, '__output__', []))

    def init(self) -> None:
        """Performs any required initialisation for the plugin."""
        getattr(self.module, 'init', lambda: None)()


## App

class LifecycleStage(Enum):
    INIT = 0
    DNS = 1
    NAT = 2
    NODES = 3
    FOOTERS = 4
    WRITE = 5
    CLEANUP = 6

class App:
    plugin_mgr: PluginManager
    """The PluginManager object."""
    APP_OUTDIRS = ('domains', 'ips', 'nodes')
    """Tuple of directories documents will be written to. 
    Relative to the output directory / PageSeeder website context."""
    REPORT_OUTPATH = ''

    def __init__(self) -> None:
        self.plugin_mgr = PluginManager()

    @property
    def output(self) -> set[str]:
        """Returns a set of names of all the files and directories written to by the app as output.
        Relative to the output dir."""
        return set(self.APP_OUTDIRS) | self.plugin_mgr.output | {
            os.path.relpath(Report.DEFAULT_OUTPATH, utils.OUTDIR)}
    
    def output_clean(self) -> None:
        """
        Removes old, populated output directories and recreates them.
        """
        pageseeder.clear_loading_zone()

        if not os.path.exists(utils.APPDIR+ 'out'):
            os.mkdir(utils.APPDIR+ 'out')
        # remove old output files
        for folder in os.scandir(utils.APPDIR+ 'out'):
            if folder.is_dir():
                shutil.rmtree(folder)
            else:
                os.remove(folder)
        
        for outfolder in self.APP_OUTDIRS:
            os.mkdir(utils.APPDIR+ 'out'+ os.sep+ outfolder)

    def fetch_config(self) -> config.NetworkConfig:
        """
        Fetches the config from PageSeeder, and updates it with 
        respect to the currently loaded plugins if necessary.

        :return: The up-to-date config object.
        :rtype: config.NetworkConfig
        """
        cfg = config.NetworkConfig.from_pageseeder()
        plugin_attrs = self.plugin_mgr.pluginAttrs
        if cfg.is_empty or (not cfg.normal_attrs) or (plugin_attrs - cfg.attrs):
            self._update_config_attrs(cfg, plugin_attrs)
        return cfg

    def _update_config_attrs(self, cfg: config.NetworkConfig, plugin_attrs: set[str]) -> None:
        """
        Updates the attributes available on the labels in the config 
        and the config template on PageSeeder using *plugin_attrs*.

        Modifies *cfg* in place.

        :param cfg: Config to update.
        :type cfg: config.NetworkConfig
        :param plugin_attrs: Names of the attributes that should be available to 
        configure on each label in the config.
        :type plugin_attrs: set[str]
        """
        # TODO find solution for config vals being dropped when the plugin is disabled
        logger.warning('Updating config template on PageSeeder.')
        config.update_template(plugin_attrs)
        cfg.update_attrs(plugin_attrs)
        with open(utils.APPDIR+ 'out/config.psml', 'w') as stream:
            stream.write(cfg.to_psml())

    def download_network(self) -> containers.Network:
        """
        Downloads the network from the remote server and returns it.

        :return: A Network object instantiated from PSML.
        :rtype: containers.Network
        """
        download_dir = utils.APPDIR + 'src/remote'
        if os.path.exists(download_dir):
            if os.path.isdir(download_dir):
                shutil.rmtree(download_dir)
            else:
                os.remove(download_dir)

        pageseeder.download_dir('website', download_dir)
        return containers.Network.from_psml(download_dir, self.plugin_mgr.nodes)

    def zip_output(self, outpath: Optional[str] = None) -> ZipFile:
        """
        Creates a ZIP from the output directories and writes it to *outpath*.

        :param outpath: The absolute path to output the zip file to, 
        defaults to '$APPDIR/src/netdox-psml.zip'
        :type outpath: str, optional
        :return: The closed ZipFile.
        :rtype: ZipFile
        """
        outpath = outpath or os.path.join(
            utils.APPDIR, 'src', 'netdox-psml.zip')
        with ZipFile(outpath, mode = 'w') as zip:
            for file in self.output:
                abspath = os.path.join(utils.OUTDIR, file)
                if os.path.isdir(abspath):
                    for child in utils.path_list(abspath, utils.OUTDIR):
                        zip.write(os.path.join(utils.OUTDIR, child), child)
                else:
                    try:
                        zip.write(abspath, file)
                    except FileNotFoundError:
                        logger.error(f'Output item does not exist: {abspath}')
        return zip

    def refresh(self, dry: bool = False) -> None:

        # Initialisation                                                    #
        self.output_clean()

        try:
            location_path = os.path.join(utils.APPDIR, 'cfg', 'locations.json')
            with open(location_path, 'r') as stream:
                locations = json.loads(stream.read())
            for key in locations:
                locations[key] = set(locations[key])
        except FileNotFoundError:
            locations = {}
        except Exception as exc:
            logger.exception('Failed to read location config.', exc_info = exc)
            locations = {}

        network = containers.Network(
            config = self.fetch_config(), 
            labels = LabelDict.from_pageseeder(),
            locations = locations
        )

        if dry: 
            logger.info('Refresh running as dry run: no documents will be uploaded.')
            remote_network = None
        else:
            logger.debug('Downloading network from remote.')
            remote_network = self.download_network()

        self.plugin_mgr.runStage(network, LifecycleStage.INIT)

        #-------------------------------------------------------------------#
        # Primary data-gathering stages                                     #
        #-------------------------------------------------------------------#
        
        self.plugin_mgr.runStage(network, LifecycleStage.DNS)
        self.plugin_mgr.runStage(network, LifecycleStage.NAT)
        self.plugin_mgr.runStage(network, LifecycleStage.NODES)

        #-------------------------------------------------------------------#
        # Generate objects for unused private IPs in used subnets,          #
        # run any pre-write plugins                                         #
        #-------------------------------------------------------------------#

        network.ips.fillSubnets()
        self.plugin_mgr.runStage(network, LifecycleStage.FOOTERS)

        #-------------------------------------------------------------------#
        # Write Network to pickle and psml,                                 #
        # scan for stale files and generate report,                         #
        # and run any post-write plugins                                    #
        #-------------------------------------------------------------------#

        network.dump()
        network.writePSML()
        self.plugin_mgr.runStage(network, LifecycleStage.WRITE)
        network.report.addSection(network.dns_report())
        network.report.addSection(
            utils.stale_report(pageseeder.findStale(self.output)))
        with open(utils.APPDIR + 'src/warnings.log', 'r') as stream:
            network.report.logs = stream.read()
        network.report.addSection(str(network.counter.generate_report()))
        network.report.writeReport()
        
        if remote_network is not None:
            logger.debug('Copying notes from remote network.')
            network.copy_notes(remote_network)

        #-------------------------------------------------------------------#
        # Zip, upload, and cleanup                                          #
        #-------------------------------------------------------------------#

        logger.debug('Network metrics: ' + json.dumps(
            {str(k): str(v) for k, v in network.counter.counts.items()}, 
        indent = 2))

        zip = self.zip_output()
        if not dry:
            pageseeder.zip_upload(zip.filename, 'website')
        else:
            logger.warning('Did not upload documents due to --dry-run flag.')

        self.plugin_mgr.runStage(network, LifecycleStage.CLEANUP)

        logger.info('Done.')

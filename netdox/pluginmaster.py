"""
This module initialises and exposes plugins as imported modules for use by Netdox and other plugins.

Initially the default plugins were baked in features, but it became obvious that in order for Netdox to be useful anywhere outside of an internal context, it needed completely modular inputs at least.
This was quickly expanded to allow custom code to be executed at multiple points of interest, which became the plugin stages.
This script may also be used to manually run a plugin or plugin stage. 
Usage is as follows: ``python3 pluginmaster.py <stage|plugin> <name>``
"""

import utils
import importlib, sys, os
from traceback import format_exc
from typing import Any, Generator, Tuple

## Initialisation

def fetchPlugins() -> Generator[Tuple[Any, os.DirEntry, str], Any, Any]:
    """
    This function scans the plugins directory for valid modules and imports if possible. It also loads the plugins stage if present.

    :Yields:
        A 3-tuple containing the module object of a plugin, an *os.DirEntry* object corresponding to the directory the plugin was found in, and the plugin stage as a string.
    """
    for plugindir in os.scandir('plugins'):
        if plugindir.is_dir() and plugindir.name != '__pycache__':
            pluginName = plugindir.name
            try:
                plugin = importlib.import_module(f'plugins.{pluginName}')
            except Exception:
                raise ImportError(f'[ERROR][plugins] Failed to import plugin {pluginName}: \n{format_exc()}')
            else:
                if hasattr(plugin, 'stage'):
                    stage = plugin.stage.lower()
                else:
                    stage = 'none'
                yield plugin, plugindir, stage

@utils.critical
def initPlugins():
    """
    Loads any valid plugins into a global dict named *pluginmap*, in which keys are any used plugin stages, aswell as an *all* stage which contains all initialised plugins.
    """
    global pluginmap
    pluginmap = {'all':{}}
    for plugin, plugindir, stage in fetchPlugins():
        if stage not in pluginmap:
            pluginmap[stage] = {}
        pluginmap[stage][plugindir.name] = plugin
        pluginmap['all'][plugindir.name] = plugin
    pluginmap = {k: pluginmap[k] for k in sorted(pluginmap)}


## Runners

def runPlugin(plugin, forward_dns: dict[str, utils.DNSRecord], reverse_dns: dict[str, utils.PTRRecord]):
    """
    Calls the top-level *runner* function of the provided plugin module object. Arguments passed to *runner* are the two dns sets (one forward and one reverse) passed to this function, which can be used for reading or writing.

    :Args:
        plugin:
            A module object returned by ``importlib.import_module``
        forward_dns:
            A dictionary where keys are unique DNS names and values are a ``utils.DNSRecord`` class describing all forward DNS records with that name.
        reverse_dns:
            A dictionary where keys are unique DNS names and values are a ``utils.PTRRecord`` class describing all reverse DNS records with that name.
    """
    print(f'[INFO][pluginmaster] Running plugin {plugin.__name__}')
    try:
        plugin.runner(forward_dns, reverse_dns)
    except Exception:
        print(f'[ERROR][pluginmaster] Running {plugin.__name__} threw an exception: \n{format_exc()}')
    else:
        print(f'[INFO][pluginmaster] Plugin {plugin.__name__} completed successfully')

def runStage(stage: str, forward_dns: dict[str, utils.DNSRecord], reverse_dns: dict[str, utils.PTRRecord]):
    """
    Calls *runPlugin* on all plugins in a specified stage.
    """
    global pluginmap
    print(f'[INFO][pluginmaster] Running all plugins in stage {stage}')
    for _, plugin in pluginmap[stage].items():
        runPlugin(plugin, forward_dns, reverse_dns)



if __name__ == '__main__':
    initPlugins()
    try:
        forward_dns = utils.loadDNS('src/dns.json')
        reverse_dns = utils.loadDNS('src/reverse.json')
    except Exception:
        raise FileNotFoundError('[ERROR][pluginmaster] Unable to load DNS')

    if sys.argv[1] and sys.argv[1] in ('stage', 'plugin'):
        if sys.argv[1] == 'stage':
            stage = sys.argv[2]
            if stage in pluginmap:
                runStage(stage, forward_dns, reverse_dns)
            else:
                raise ValueError(f'[ERROR][pluginmaster] Uknown stage: {stage}')
        elif sys.argv[1] == 'plugin':
            plugin = sys.argv[2]
            found = False
            for stage, pluginset in pluginmap.items():
                if plugin in pluginset:
                    runPlugin(pluginset[plugin], forward_dns, reverse_dns)
                    found = True
            if not found:
                raise ImportError(f'[ERROR][pluginmaster] Plugin {plugin} not found')
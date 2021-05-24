import utils
import importlib, sys, os
from traceback import format_exc
from typing import Any, Generator, Tuple

## Initialisation

def fetchPlugins() -> Generator[Tuple[Any, os.DirEntry, int], Any, Any]:
    """
    Generator which yields a 3-tuple of a plugin, the location of said plugin, and an optional stage at which to run
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
    Fetches all plugins and sorts them by stage
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

def runPlugin(plugin, forward_dns: dict[str, utils.DNSRecord], reverse_dns: dict[str, utils.DNSRecord]):
    """
    Runs a single plugin via it's runner
    """
    print(f'[INFO][pluginmaster] Running plugin {plugin.__name__}')
    try:
        plugin.runner(forward_dns, reverse_dns)
    except Exception:
        print(f'[ERROR][pluginmaster] Running {plugin.__name__} threw an exception: \n{format_exc()}')
    else:
        print(f'[INFO][pluginmaster] Plugin {plugin.__name__} completed successfully')

def runStage(stage: str, forward_dns: dict[str, utils.DNSRecord], reverse_dns: dict[str, utils.DNSRecord]):
    """
    Runs all initialised plugins in a given stage.
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
                    runPlugin(plugin, forward_dns, reverse_dns)
                    found = True
            if not found:
                raise ImportError(f'[ERROR][pluginmaster] Plugin {plugin} not found')
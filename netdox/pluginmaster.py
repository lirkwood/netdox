import utils
import importlib, os
from traceback import format_exc
from typing import Any, Callable, Generator, Tuple

def fetchPlugins() -> Generator[Tuple[Callable[[dict[str, utils.DNSRecord], dict[str, utils.DNSRecord]], None], os.DirEntry, int], Any, Any]:
    """
    Generator which yields a 3-tuple of a plugins main function, the location of said plugin, and a integer value used to decide execution order.
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
                    stage = plugin.stage
                else:
                    stage = 'none'
                yield plugin, plugindir, stage

@utils.critical
def initPlugins():
    """
    Fetches all plugins and sorts them by stage
    """
    global pluginmap
    pluginmap = {}
    for plugin, plugindir, stage in fetchPlugins():
        if stage not in pluginmap:
            pluginmap[stage] = {}
        pluginmap[stage][plugindir.name] = plugin
    pluginmap = {k: pluginmap[k] for k in sorted(pluginmap)}


@utils.critical
def runStage(stage: str, forward_dns: dict[str, utils.DNSRecord], reverse_dns: dict[str, utils.DNSRecord]):
    """
    Runs all initialised plugins in a given stage.
    """
    global pluginmap
    for pluginName, plugin in pluginmap[stage].items():
        print(f'[INFO][pluginmaster][{stage}] Running plugin {pluginName}')
        try:
            plugin.runner(forward_dns, reverse_dns)
        except Exception:
            print(f'[ERROR][pluginmaster][{stage}] Running {pluginName} threw an exception: \n{format_exc()}')
        else:
            print(f'[INFO][pluginmaster][{stage}] Plugin {pluginName} completed successfully')

if __name__ == '__main__':
    initPlugins()
    runPlugins({},{})
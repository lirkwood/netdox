import utils
import importlib, os
from traceback import format_exc
from typing import Any, Callable, Generator, Tuple

def fetchRunners() -> Generator[Tuple[Callable[[dict[str, utils.DNSRecord], dict[str, utils.DNSRecord]], None], os.DirEntry, int], Any, Any]:
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
                    stage = 99
                yield plugin.runner, plugindir, stage

@utils.critical
def initPlugins():
    """
    Fetches all plugins and sorts them by stage
    """
    global pluginmap
    pluginmap = {}
    for runner, plugindir, stage in fetchRunners():
        if stage not in pluginmap:
            pluginmap[stage] = {}
        pluginmap[stage][plugindir.name] = runner
    pluginmap = sorted(pluginmap)


@utils.critical
def runPlugins(forward_dns: dict[str, utils.DNSRecord], reverse_dns: dict[str, utils.DNSRecord]):
    """
    Runs all plugins in order.
    """
    global pluginmap
    for index, stage in pluginmap.items():
        for plugin, runner in stage.items():
            print(f'[INFO][pluginmaster] Running plugin {plugin} as part of stage {index}')
            try:
                runner(forward_dns, reverse_dns)
            except Exception:
                print(f'[ERROR][pluginmaster] Running {plugin} threw an exception: \n{format_exc()}')
            else:
                print(f'[INFO][pluginmaster] Plugin {plugin} completed successfully')

if __name__ == '__main__':
    runPlugins({})
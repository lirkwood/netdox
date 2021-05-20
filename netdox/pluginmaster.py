import utils
import importlib, os
from traceback import format_exc
from typing import Any, Callable, Generator, Tuple

def fetchRunners() -> Generator[Tuple[Callable[[dict[str, utils.DNSRecord], dict[str, utils.DNSRecord]], None], os.DirEntry], Any, Any]:
    for plugindir in os.scandir('plugins'):
        if plugindir.is_dir() and plugindir.name != '__pycache__':
            pluginName = plugindir.name
            try:
                plugin = importlib.import_module(f'plugins.{pluginName}')
            except Exception:
                raise ImportError(f'[ERROR][plugins] Failed to import plugin {pluginName}: \n{format_exc()}')
            else:
                yield plugin.runner, plugindir

@utils.critical
def runPlugins(forward_dns: dict[str, utils.DNSRecord], reverse_dns: dict[str, utils.DNSRecord]):
    for runner, plugindir in fetchRunners():
        pluginName = plugindir.name
        print(f'[INFO][pluginmaster] Discovered plugin {pluginName}')
        try:
            runner(forward_dns, reverse_dns)
        except Exception:
            print(f'[ERROR][pluginmaster] Running {pluginName} threw an exception: \n{format_exc()}')
        else:
            print(f'[INFO][pluginmaster] Plugin {pluginName} completed successfully')

if __name__ == '__main__':
    runPlugins({})
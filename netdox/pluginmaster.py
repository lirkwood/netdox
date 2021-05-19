import utils
import importlib, os
from traceback import format_exc
from typing import Any, Generator, Iterable, Tuple

def fetchRunners() -> Generator[Tuple[Any, os.DirEntry], Any, Any]:
    for plugindir in os.scandir('plugins'):
        if plugindir.is_dir():
            pluginName = plugindir.name
            pluginfiles = [file.name for file in os.scandir(plugindir) if file.is_file()]
            if 'writer.xsl' in pluginfiles:
                try:
                    plugin = importlib.import_module(f'plugins.{pluginName}')
                except Exception:
                    raise ImportError(f'[ERROR][plugins] Failed to import plugin {pluginName}: \n{format_exc()}')
                else:
                    yield plugin.runner, plugindir

@utils.critical
def runPlugins(dns_set: dict[str, utils.dns]):
    for runner, plugindir in fetchRunners():
        pluginName = plugindir.name
        print(f'[INFO][pluginmaster] Discovered plugin {pluginName}')
        try:
            dnslinks  = runner()
        except Exception:
            print(f'[ERROR][pluginmaster] Running {pluginName} threw an exception: \n{format_exc()}')
        else:
            for name, locator in dnslinks.items():
                dns = dns_set[name]
                if isinstance(locator, str):
                    dns.link(locator, pluginName)
                elif isinstance(locator, Iterable):
                    for _locator in locator:
                        dns.link(_locator, pluginName)
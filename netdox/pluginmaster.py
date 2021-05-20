import utils
import importlib, os
from traceback import format_exc
from typing import Any, Generator, Iterable, Tuple

def fetchRunners() -> Generator[Tuple[Any, os.DirEntry], Any, Any]:
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
def runPlugins(forward_dns: dict[str, utils.dns], reverse_dns: dict[str, utils.dns]):
    for runner, plugindir in fetchRunners():
        pluginName = plugindir.name
        print(f'[INFO][pluginmaster] Discovered plugin {pluginName}')
        try:
            dnslinks_f, dnslinks_r = runner(forward_dns, reverse_dns)
        except Exception:
            print(f'[ERROR][pluginmaster] Running {pluginName} threw an exception: \n{format_exc()}')
        else:
            for dns_set, linkset in [(forward_dns, dnslinks_f),(reverse_dns, dnslinks_r)]:
                for name, locator in linkset.items():
                    if name in dns_set:
                        dns = dns_set[name]
                        if isinstance(locator, str):
                            dns.link(locator, pluginName)
                        elif isinstance(locator, Iterable):
                            for _locator in locator:
                                dns.link(_locator, pluginName)

if __name__ == '__main__':
    runPlugins({})
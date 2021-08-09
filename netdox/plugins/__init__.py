"""
Provides a base class for writing Plugins
"""

from abc import ABC, abstractmethod

from networkobjs import Network


class BasePlugin(ABC):
    """
    Base class for plugins
    """
    name: str
    """The name to be used for logs, in documents, etc."""
    stages: list[str]
    """The stages to call runner at"""
    node_types: tuple[str] = ()
    """The node types that this plugin adds to the network (if any)"""

    def init(self) -> None:
        """
        Any initialisation that should be done before the runner is called.
        """
        pass

    @abstractmethod
    def runner(self, network: Network) -> None:
        """
        The main function of the plugin.
        """
        pass
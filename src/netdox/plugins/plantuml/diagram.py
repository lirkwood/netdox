import logging
from typing import Optional

from netdox import Network, Node
from netdox.base import NetworkObject
from netdox.dns import DNSObject, IPv4Address
from netdox.nodes import ProxiedNode
from plantuml import deflate_and_encode
import requests

logger = logging.getLogger(__name__)

class NodeDiagramFactory:
    server: str
    """The hostname + path of the PlantUML server to use."""
    markup: list[str]
    """The markup to send to the server, as a list of lines."""
    links: list[str]
    """Markup for links between classes, to append to main body."""
    HEADER = (
        '@startuml', 
        'set namespaceSeparator none',
        'skinparam shadowing false',
        'skinparam package<<Layout>> {',
            'borderColor Transparent',
            'backgroundColor Transparent',
            'fontColor Transparent',
            'stereotypeFontColor Transparent',
        '}'
    )
    """Some markup to insert at the top."""
    _node: Optional[Node]

    def __init__(self, server: str = None, https: bool = True) -> None:
        """
        Constructor.

        :param server: The PlantUML server hostname + path. Defaults to public server.
        :type server: PlantUML, optional
        """
        self.server = (server or 'www.plantuml.com/plantuml').strip('/')
        self.scheme = 'https' if https else 'http'
        self.markup = []
        self.links = []
        self._node = None

    def _class_name(self, nwobj: NetworkObject) -> str:
        """Returns the UML class name for an object."""
        return f'{nwobj.__class__.__name__}: {nwobj.name}'

    def _class_definition(self, name: str, color: str = None) -> str:
        """Returns the UML class definition line for a given class name."""
        return f'class "{name}" {f"#{color}" if color else ""} {{'

    def draw(self, node: Node) -> str:
        """
        Generate diagram for the given node and return the SVG.

        :param node: The node to draw.
        :type node: Node
        :return: An SVG.
        :rtype: str
        """
        return requests.get(
            f'{self.scheme}://{self.server}/svg/{deflate_and_encode(self._build_markup(node))}'
        ).content.decode('utf-8')

    def _build_markup(self, node: Node) -> str:
        """
        Generate markup for the diagram of the given node.

        :param node: The node to generate markup for.
        :type node: Node
        :return: The markup for the diagram.
        :rtype: str
        """
        self._node = node
        self._node_name = self._class_name(node)
        self.links = []
        self.markup = [
            self._class_definition(self._node_name),
                f'identity: {node.identity}',
                f'type: {node.type}',
            '}',
        ]

        if isinstance(node, ProxiedNode):
            # draw proxy and link it to node, then resolve node addrs to proxy
            if node.proxy.node:
                proxy_name = self._class_name(node.proxy.node)

                self.markup.extend([
                    self._class_definition(proxy_name),
                        f'identity: {node.proxy.node.identity}',
                        f'type: {node.proxy.node.type}',
                    '}'])
                for addr in node.proxy.addresses:
                    self._link(proxy_name, annotation = addr)

                self._node = node.proxy.node
                self._node_name = proxy_name
            else:
                logger.debug(f'No proxy node for {node.identity}')
                # TODO add placeholder proxy node to fill out diagram in this case
            
        self.markup.append('package dns <<Layout>>{',)
        cache: set[str] = set()
        for domain in node.domains:
            cache |= self._draw_dns(node.network.find_dns(domain), cache)
        for ip in node.ips:
            cache |= self._draw_dns(node.network.find_dns(ip), cache)

        self.markup.extend(self.links)
        self.markup.append('}@enduml')
        return '\n'.join((*self.HEADER, *self.markup, *self.links))

    def _draw_dns(self, dnsobj: DNSObject, cache: set[str] = None) -> set[str]:
        """
        Recursively adds a DNSObject and its records/backrefs to the diagram.

        :param dnsobj: The DNSObject to draw.
        :type dnsobj: DNSObject
        :param cache: A set of DNSObject names that have already been drawn,
        defaults to None
        :type cache: set[str], optional
        :return: The cache.
        :rtype: set[str]
        """
        assert self._node is not None, 'Cannot draw DNS records to nonexistent node.'
        cache = cache or set()
        if dnsobj.name in cache:
            return cache
        cache.add(dnsobj.name)

        class_name = self._class_name(dnsobj)
        self.markup.extend([
            self._class_definition(class_name),
                f'link: [[https://{dnsobj.name}/]]',
                f'zone: {dnsobj.zone}',
            '}'
        ])

        for record in dnsobj.links:
            cache |= self._draw_dns(record.destination, cache)
            dest_name = self._class_name(record.destination)
            self._link(class_name, dest_name, record.source)

        if isinstance(dnsobj, IPv4Address):
            for entry in dnsobj.NAT:
                cache |= self._draw_dns(entry.destination, cache)
                dest_name = self._class_name(entry.destination)
                self._link(class_name, dest_name, entry.source)

            if dnsobj.node is not None:
                node_class_name = self._class_name(dnsobj.node)
                if self._class_definition(node_class_name) in self.markup:
                    self._link(class_name, node_class_name)

        return cache

    def _link(self, 
            origin: str, 
            destination: str = None, 
            annotation: str = None
        ) -> None:
        """
        Links from the UML class at *origin* to the current node, 
        or the UML class with name *destination* instead if specified.

        :param origin: The name of the UML class to link from.
        :type origin: str
        :param destination: The name of the DNSObject to link to.
        :type destination: str
        """
        destination = destination or self._node_name
        annotation = f' : {annotation}' if annotation else ''
        link = f'"{origin}" --> "{destination}"{annotation}'
        if link not in self.markup:
            self.markup.append(link)


if __name__ == '__main__':
    net = Network.from_dump()
    factory = NodeDiagramFactory()
    for node in net.nodes:
        print(factory.draw(node))
        exit(0)

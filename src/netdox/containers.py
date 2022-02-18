"""
This module contains any container classes.
"""
from __future__ import annotations

import logging
import pickle
from typing import Iterable, Iterator, Sequence, Type, Union

from netdox import base, dns, helpers, iptools, nodes
from netdox.config import NetworkConfig
from netdox.iptools import valid_ip
from netdox.utils import APPDIR, Cryptor, valid_domain

logger = logging.getLogger(__name__)


class DomainSet(dns.DNSObjectContainer[dns.Domain]):
    """
    Container for a set of Domains
    """
    objects: dict[str, dns.Domain]
    objectType: str = 'domains'
    objectClass: Type[dns.Domain] = dns.Domain

    ## dunder methods

    def __init__(self, network: Network, domains: Iterable[dns.Domain] = []) -> None:
        super().__init__(network, domains)

    def __getitem__(self, key: str) -> dns.Domain:
        return super().__getitem__(key)

    ## Re-implemented to type hint
    def __iter__(self) -> Iterator[dns.Domain]:
        yield from super().__iter__()

    ## properties

    @property
    def domains(self) -> dict[str, dns.Domain]:
        """
        Returns the underlying objects dict.

        :return: A dictionary of the Domains in this set, with names as keys.
        :rtype: dict
        """
        return self.objects


class IPv4AddressSet(dns.DNSObjectContainer[dns.IPv4Address]):
    """
    Container for a set of IPv4Address
    """
    objects: dict[str, dns.IPv4Address]
    objectType: str = 'ips'
    objectClass: Type[dns.IPv4Address] = dns.IPv4Address
    subnets: set
    """A set of the /24 subnets of the private IPs in this container."""

    def __init__(self, network: Network, ips: list[dns.IPv4Address] = []) -> None:
        super().__init__(network, ips)
        self.subnets = set()

    def __getitem__(self, key: str) -> dns.IPv4Address:
        return super().__getitem__(key)

    def __iter__(self) -> Iterator[dns.IPv4Address]:
        yield from super().__iter__()

    @property
    def ips(self) -> dict[str, dns.IPv4Address]:
        """
        Returns the underlying objects dict.

        :return: A dictionary of the IPv4Addresses in this set, with addresses as keys.
        :rtype: dict
        """
        return self.objects

    @property
    def private_ips(self) -> list[dns.IPv4Address]:
        """
        Returns all IPs in the set that are part of the private namespace

        :return: A list of IPv4Address objects
        :rtype: list[IPv4Address]
        """
        return [ip for ip in self if ip.is_private]

    @property
    def public_ips(self) -> list[dns.IPv4Address]:
        """
        Returns all IPs in the set that are not part of the private namespace

        :return: A list of IPv4Address objects
        :rtype: list[IPv4Address]
        """
        return [ip for ip in self if not ip.is_private]

    @property
    def unused(self) -> list[dns.IPv4Address]:
        """
        Returns all IPs in the set that are not referenced by a DNS record.

        :return: A list of IPv4Address objects
        :rtype: list[IPv4Address]
        """
        return [ip for ip in self if ip.unused]

    @property
    def used(self) -> list[dns.IPv4Address]:
        """
        Returns all IPs in the set that are referenced by a DNS record.

        :return: A list of IPv4Address objects
        :rtype: list[IPv4Address]
        """
        return [ip for ip in self if not ip.unused]

    def fillSubnets(self) -> None:
        """
        Iterates over each unique private subnet this set has IP addresses in, 
        and generates IPv4Addresses for each IP in the subnet not already in the set.
        """
        for subnet in self.subnets:
            for ip in iptools.subn_iter(subnet):
                self[ip]


class NodeSet(base.NetworkObjectContainer[nodes.Node]):
    """
    Container for a set of Nodes
    """
    objects: dict[str, nodes.Node]
    objectType: str = 'nodes'
    objectClass: Type[nodes.Node] = nodes.Node

    def __init__(self, network: Network, nodeSet: list[nodes.Node] = []) -> None:
        self.objects = {node.identity: node for node in nodeSet}
        self.network = network

    def __getitem__(self, key: str) -> nodes.Node:
        return super().__getitem__(key)

    def __iter__(self) -> Iterator[nodes.Node]:
        yield from super().__iter__()

    def __contains__(self, key: Union[str, nodes.Node]) -> bool:
        if isinstance(key, str):
            return super().__contains__(key)
        else:
            return super().__contains__(key.identity)

    @property
    def nodes(self) -> dict[str, nodes.Node]:
        """
        Returns the underlying objects dict

        :return: A dictionary of the Nodes in the set, with identities as keys
        :rtype: dict[str, Node]
        """
        return self.objects

    ## ref handling

    def addRef(self, node: nodes.Node, ref: str) -> None: # type: ignore
        """
        Adds a pointer from *ref* to *node* as long as it is present in the network.

        :param node: The node to point *ref* to.
        :type node: nodes.Node
        :param ref: The identifier which can now be used to find *node*.
        :type ref: str
        :raises RuntimeError: If the node is not in the same network.
        """
        if node.network is self.network:
            self[ref] = node
        else:
            raise RuntimeError('Cannot add ref to a node in a different network.')


class Network:
    """
    A container for NetworkObjectContainers.
    Also contains helper classes and other data that pertains to NetworkObjects.
    """
    domains: DomainSet
    """A NetworkObjectContainer for the Domains in the network."""
    ips: IPv4AddressSet
    """A NetworkObjectContainer for the IPv4Addresses in the network."""
    nodes: NodeSet
    """A NetworkObjectContainer for the Nodes in the network."""
    config: NetworkConfig
    """The network specific config."""
    labels: helpers.LabelDict
    """A defaultdict mapping document docids to their applied labels."""
    locator: helpers.Locator
    """A helper class to provide location data to Nodes."""
    report: helpers.Report
    """A helper class to report network changes."""
    cache: set
    """A set of cached names. Used when resolving long record chains."""

    def __init__(self, 
            domains: DomainSet = None, 
            ips: IPv4AddressSet = None, 
            nodes: NodeSet = None,
            config: NetworkConfig = None,
            labels: helpers.LabelDict = None
        ) -> None:
        """
        Instantiate a Network object.

        :param domains: A DomainSet to include in the network, defaults to None
        :type domains: DomainSet, optional
        :param ips: A IPv4AddressSet to include in the network, defaults to None
        :type ips: IPv4AddressSet, optional
        :param nodes: A NodeSet to include in the network, defaults to None
        :type nodes: NodeSet, optional
        :param config: A NetworkConfig object.
        :type config: dict, optional
        """

        self.domains = domains or DomainSet(network = self)
        self.ips = ips or IPv4AddressSet(network = self)
        self.nodes = nodes or NodeSet(network = self)

        self.config = config or NetworkConfig()
        self.labels = labels or helpers.LabelDict()
        
        self.locator = helpers.Locator()
        self.report = helpers.Report()
        self.cache = set()

    def link(self, 
            origin: Union[str, dns.DNSObject], 
            dest: Union[str, dns.DNSObject], 
            source: str
        ) -> None:
        """
        Creates a DNS record from *origin* to *dest* provided by *source*,
        if both origin and dest are valid DNS objects / DNSObj names.

        :param origin: DNSObject or name of the starting point for the new DNS record.
        :type origin: Union[str, dns.DNSObject]
        :param dest: Destination for the new DNS record.
        :type dest: Union[str, dns.DNSObject]
        :param source: Name of the plugin that provided this DNS record.
        :type source: str
        """
        if isinstance(origin, str):
            if (origin not in self.config.exclusions
                and (valid_ip(origin) or valid_domain(origin))
            ):
                origin = self.find_dns(origin)
            else:
                return

        if isinstance(dest, dns.DNSObject):
            dest = dest.name
        if (dest not in self.config.exclusions
            and (valid_ip(dest) or valid_domain(dest))
        ):
            origin.link(dest, source)

    ## resolving refs

    def find_dns(self, name: str) -> dns.DNSObject:
        """
        Returns a DNSObject from its name.

        :param name: The name of the DNSObject.
        :type name: str
        :return: A Domain or IPv4Address
        :rtype: Union[nwobjs.Domain, nwobjs.IPv4Address]
        """
        return self.ips[name] if iptools.valid_ip(name) else self.domains[name]

    def _resolvesTo(self, startObj: dns.DNSObject, target: str) -> bool:
        """
        Returns a bool based on if *startObj* resolves to *target*.

        :param startObj: The DNSObject to start with.
        :type startObj: base.DNSObject
        :param target: The name of the target DNSObject to test.
        :type target: str
        :return: A boolean value.
        :rtype: bool
        """
        if isinstance(startObj, str):
            startObj = self.find_dns(startObj)
        if isinstance(target, dns.DNSObject):
            target = target.name

        if startObj in self.cache:
            return False
        self.cache.add(startObj)
        
        if target in startObj.records.names:
            return True

        for dest in startObj.records.destinations:
            if self._resolvesTo(dest, target):
                return True
        
        if isinstance(startObj, dns.IPv4Address):
            for entry in startObj.NAT:
                if (
                    entry.destination.name == target or
                    self._resolvesTo(entry.destination, target)
                ):
                    return True

        return False

    def resolvesTo(self, 
            startObj: Union[dns.DNSObject, str], 
            target: Union[dns.DNSObject, str]
        ) -> bool:
        """
        Returns a bool based on if *startObj* resolves to *target*.

        :param startObj: The DNSObject to start with.
        :type startObj: base.DNSObject
        :param target: The target DNSObject to test.
        :type target: base.DNSObject
        :return: A boolean value.
        :rtype: bool
        """
        if isinstance(startObj, str):
            startObj = self.find_dns(startObj)
        if isinstance(target, dns.DNSObject):
            target = target.name
        self.cache.clear()
        return self._resolvesTo(startObj, target)


    ## Serialisation

    def dump(self, outpath: str = APPDIR + 'src/network.bin', encrypt = True) -> None:
        """
        Pickles the Network object and saves it to *path*, encrypted.

        :param outpath: The path to save dump the network to, defaults to 'src/network.bin' within *APPDIR*.
        :type outpath: str, optional
        :param encrypt: Whether or not to encrypt the dump, defaults to True
        :type encrypt: bool, optional
        """
        network = pickle.dumps(self)
        with open(outpath, 'wb') as nw:
            nw.write(Cryptor().encrypt(network) if encrypt else network)

    @classmethod
    def fromDump(cls: Type[Network], inpath: str = APPDIR + 'src/network.bin', encrypted = True) -> Network:
        """
        Instantiates a Network from a pickled dump.

        :param cls: The Network class, passed implicitly
        :type cls: Type[Network]
        :param inpath: Path to the binary network file, defaults to 'src/network.bin'
        :type inpath: str, optional
        :param encrypted: Whether or not the dump is encrypted, defaults to True
        :type encrypted: bool, optional
        :return: The pickled network object at *inpath*.
        :rtype: Network
        """
        with open(inpath, 'rb') as nw:
            return pickle.loads(
                Cryptor().decrypt(nw.read())
                if encrypted else nw.read()
            )

    def writePSML(self) -> None:
        """
        Writes the domains, ips, and nodes of a network to PSML using ``self.writer``.
        """
        for nwobj in (*self.domains, *self.ips, *self.nodes):
            try:
                nwobj.serialise()
            except Exception as exc:
                logger.exception(exc)
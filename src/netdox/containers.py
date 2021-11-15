"""
This module contains any container classes.
"""
from __future__ import annotations

from typing import Iterable, Iterator, Type, Union
import pickle

from netdox import iptools
from netdox import base, helpers, nwobjs
from netdox.config import NetworkConfig
from netdox.utils import APPDIR, Cryptor


class DomainSet(base.DNSObjectContainer[nwobjs.Domain]):
    """
    Container for a set of Domains
    """
    objects: dict[str, nwobjs.Domain]
    objectType: str = 'domains'
    objectClass: Type[nwobjs.Domain] = nwobjs.Domain

    ## dunder methods

    def __init__(self, network: Network, domains: Iterable[nwobjs.Domain] = []) -> None:
        super().__init__(network, domains)

    def __getitem__(self, key: str) -> nwobjs.Domain:
        return super().__getitem__(key)

    ## Re-implemented to type hint
    def __iter__(self) -> Iterator[nwobjs.Domain]:
        yield from super().__iter__()

    ## properties

    @property
    def domains(self) -> dict[str, nwobjs.Domain]:
        """
        Returns the underlying objects dict.

        :return: A dictionary of the Domains in this set, with names as keys.
        :rtype: dict
        """
        return self.objects


class IPv4AddressSet(base.DNSObjectContainer[nwobjs.IPv4Address]):
    """
    Container for a set of IPv4Address
    """
    objects: dict[str, nwobjs.IPv4Address]
    objectType: str = 'ips'
    objectClass: Type[nwobjs.IPv4Address] = nwobjs.IPv4Address
    subnets: set
    """A set of the /24 subnets of the private IPs in this container."""

    def __init__(self, network: Network, ips: list[nwobjs.IPv4Address] = []) -> None:
        super().__init__(network, ips)
        self.subnets = set()

    def __getitem__(self, key: str) -> nwobjs.IPv4Address:
        return super().__getitem__(key)

    def __iter__(self) -> Iterator[nwobjs.IPv4Address]:
        yield from super().__iter__()

    @property
    def ips(self) -> dict[str, nwobjs.IPv4Address]:
        """
        Returns the underlying objects dict.

        :return: A dictionary of the IPv4Addresses in this set, with addresses as keys.
        :rtype: dict
        """
        return self.objects

    @property
    def private_ips(self) -> list[nwobjs.IPv4Address]:
        """
        Returns all IPs in the set that are part of the private namespace

        :return: A list of IPv4Address objects
        :rtype: list[IPv4Address]
        """
        return [ip for ip in self if ip.is_private]

    @property
    def public_ips(self) -> list[nwobjs.IPv4Address]:
        """
        Returns all IPs in the set that are not part of the private namespace

        :return: A list of IPv4Address objects
        :rtype: list[IPv4Address]
        """
        return [ip for ip in self if not ip.is_private]

    @property
    def unused(self) -> list[nwobjs.IPv4Address]:
        """
        Returns all IPs in the set that are not referenced by a DNS record.

        :return: A list of IPv4Address objects
        :rtype: list[IPv4Address]
        """
        return [ip for ip in self if ip.unused]

    @property
    def used(self) -> list[nwobjs.IPv4Address]:
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


class NodeSet(base.NetworkObjectContainer[nwobjs.Node]):
    """
    Container for a set of Nodes
    """
    objects: dict[str, nwobjs.Node]
    objectType: str = 'nodes'
    objectClass: Type[nwobjs.Node] = nwobjs.Node

    def __init__(self, network: Network, nodeSet: list[nwobjs.Node] = []) -> None:
        self.objects = {node.identity: node for node in nodeSet}
        self.network = network

    def __getitem__(self, key: str) -> nwobjs.Node:
        return super().__getitem__(key)

    def __iter__(self) -> Iterator[nwobjs.Node]:
        yield from super().__iter__()

    def __contains__(self, key: Union[str, nwobjs.Node]) -> bool:
        if isinstance(key, str):
            return super().__contains__(key)
        else:
            return super().__contains__(key.identity)

    @property
    def nodes(self) -> dict[str, nwobjs.Node]:
        """
        Returns the underlying objects dict

        :return: A dictionary of the Nodes in the set, with identities as keys
        :rtype: dict[str, Node]
        """
        return self.objects

    ## ref handling

    def addRef(self, node: nwobjs.Node, ref: str) -> None:
        """
        Adds a pointer from *ref* to *node* as long as it is present in the network.

        :param node: The node to point *ref* to.
        :type node: nwobjs.Node
        :param ref: The identifier which can now be used to find *node*.
        :type ref: str
        :raises RuntimeError: If the node is not in the same network.
        """
        if node.network is self.network:
            self[ref] = node
        else:
            raise RuntimeError('Cannot add ref to a node in a different network.')

    def resolveRefs(self, node_identity: str, dnsobj_name: str, cache: set[str] = None) -> set[str]:
        """
        Creates noderefs from the DNSObj at *dnsobj_name* (and DNSObjs which resolve to it) to the node with *node_identity*.

        :param node_identity: The identity of the target node.
        :type node_identity: str
        :param dnsobj_name: The name of the DNSObj to link from.
        :type dnsobj_name: str
        :param cache: A set of DNSObject names to ignore, defaults to None
        :type cache: set[str], optional
        :return: The set of DNSObject names that have been tested, including cached names.
        :rtype: set[str]
        """
        node = self[node_identity]
        if not cache:
            cache = set()
        elif dnsobj_name in cache:
            return cache
        cache.add(dnsobj_name)

        dnsobj: base.DNSObject
        if dnsobj_name in self.network.ips:
            dnsobj = self.network.ips[dnsobj_name]
            dnsobj_set = node.ips

        elif dnsobj_name in self.network.domains:
            dnsobj = self.network.domains[dnsobj_name]
            dnsobj_set = node.domains
        
        else: return cache

        if dnsobj.node: 
            if dnsobj.node.type == 'placeholder':
                dnsobj.node.merge(node)
            return cache

        dnsobj_set.add(dnsobj.name)
        dnsobj.node = node
        
        for backrefs in dnsobj.backrefs.values():
            for backref in backrefs:
                cache |= self.resolveRefs(node_identity, backref, cache)

        if isinstance(dnsobj, nwobjs.IPv4Address) and dnsobj.nat:
            cache |= self.resolveRefs(node_identity, dnsobj.nat, cache)

        return cache


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

    ## resolving refs

    def resolvesTo(self, startObj: Union[base.DNSObject, str], target: Union[base.DNSObject, str]) -> bool:
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
            startObj = self.ips[startObj] if startObj in self.ips else self.domains[startObj]
        if isinstance(target, str):
            target = self.ips[target] if target in self.ips else self.domains[target]
        self.cache.add(startObj.name)

        for set in ('ips', 'domains'):
            networkSet = getattr(self, set)
            objSet = getattr(startObj, set)

            if set == 'ips' and isinstance(startObj, nwobjs.IPv4Address) and startObj.nat:
                objSet.add(startObj.nat)

            for name in objSet:
                if name not in self.cache:
                    if name == target.name:
                        self.cache.clear()
                        return True

                    elif name in networkSet and self.resolvesTo(networkSet[name], target):
                        return True
        return False

    ## Serialisation

    def dump(self, outpath: str = APPDIR + 'src/network.bin', encrypt = True) -> None:
        """
        Pickles the Network object and saves it to *path*, encrypted.

        :param outpath: The path to save dump the network to, defaults to 'src/network.bin' within *APPDIR*.
        :type outpath: str, optional
        :param encrypt: Whether or not to encrypt the dump, defaults to True
        :type encrypt: bool, optional
        """
        with open(outpath, 'wb') as nw:
            nw.write(
                Cryptor().encrypt(pickle.dumps(self))
                if encrypt else pickle.dumps(self)
            )

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
        for domain in self.domains:
            domain.serialise()
        for ip in self.ips:
            ip.serialise()
        for node in self.nodes:
            node.serialise()
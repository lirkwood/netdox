"""
This module contains any container classes.
"""
from __future__ import annotations

from typing import Iterable, Iterator, Type, Union
import pickle

from netdox import iptools
from netdox.objs import base, helpers, nwobjs
from netdox.utils import DEFAULT_DOMAIN_ROLES, APPDIR, Cryptor


class DomainSet(base.DNSObjectContainer):
    """
    Container for a set of Domains
    """
    objectType: str = 'domains'
    objectClass: Type[nwobjs.Domain] = nwobjs.Domain
    _roles: dict

    ## dunder methods

    def __init__(self, network: Network, domains: Iterable[nwobjs.Domain] = [], roles: dict = None) -> None:
        super().__init__(network, domains)
        self._roles = roles or DEFAULT_DOMAIN_ROLES

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
    
    @property
    def roles(self) -> dict[str, list[str]]:
        """
        Returns dictionary of roles and their domains (except the *exclusions* role)

        :return: A dictionary of lists of FQDNs
        :rtype: dict
        """
        try:
            return {k: v['domains'] for k, v in self._roles.items() if k != 'exclusions'}
        except KeyError:
            raise AttributeError(f'One or more domain roles are missing the property \'domains\'.')

    @roles.setter
    def roles(self, value: dict) -> None:
        """
        Sets the _roles attribute

        :param value: The new value for the _role attribute
        :type value: dict
        """
        self._roles = value

    @roles.deleter
    def roles(self) -> None:
        """
        Deletes the _roles attribute
        """
        del self._roles

    @property
    def exclusions(self) -> list[str]:
        """
        Returns a list of excluded domains

        :return: A list of FQDNs
        :rtype: list[str]
        """
        return self._roles['exclusions']\


class IPv4AddressSet(base.DNSObjectContainer):
    """
    Container for a set of IPv4Address
    """
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
        and generates IPv4Addresses for each IP in the subnet not already in the set (with the unused attribute set).
        If the set has a Network, any IPs referenced by a domain/node not already present will be generated as well.
        """
        for subnet in self.subnets:
            for ip in iptools.subn_iter(subnet):
                if ip not in self:
                    self[ip] = nwobjs.IPv4Address(self.network, ip, True)


class NodeSet(base.NetworkObjectContainer):
    """
    Container for a set of Nodes
    """
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

    def consumePlaceholder(self, placeholder: nwobjs.PlaceholderNode, replacement: nwobjs.Node) -> None:
        """
        Merges *replacement* with *placeholder*, 
        then replaces all refs to *placeholder* to refs to *replacement*.

        :param placeholder: The PlaceholderNode to consume.
        :type placeholder: nwobjs.PlaceholderNode
        :param replacement: The replacement Node, which will consume *placeholder*.
        :type replacement: nwobjs.Node
        """
        replacement.merge(placeholder)
        for domain in placeholder.domains:
            self.network.domains[domain].node = replacement
        for ip in placeholder.ips:
            self.network.ips[ip].node = replacement

        self[placeholder.identity] = replacement
        for alias in placeholder.aliases:
            self[alias] = replacement


class Network:
    """
    Container for sets of network objects.
    """
    domains: DomainSet
    """A NetworkObjectContainer for the Domains in the network."""
    ips: IPv4AddressSet
    """A NetworkObjectContainer for the IPv4Addresses in the network."""
    nodes: NodeSet
    """A NetworkObjectContainer for the Nodes in the network."""
    config: dict
    """The currently loaded config."""
    cache: set
    """A set of cached names. Used when resolving long record chains."""

    def __init__(self, 
            domains: DomainSet = None, 
            ips: IPv4AddressSet = None, 
            nodes: NodeSet = None,
            domainroles: dict = None
        ) -> None:
        """
        Instantiate a Network object.

        :param domains: A DomainSet to include in the network, defaults to None
        :type domains: DomainSet, optional
        :param ips: A IPv4AddressSet to include in the network, defaults to None
        :type ips: IPv4AddressSet, optional
        :param nodes: A NodeSet to include in the network, defaults to None
        :type nodes: NodeSet, optional
        :param config: A dictionary of config values like that returned by ``utils.config()``, defaults to None
        :type config: dict, optional
        :param roles: A dictionary of role configuration values to pass to the DomainSet of the network, defaults to None
        :type roles: dict, optional
        """

        self.domains = domains or DomainSet(network = self, roles = domainroles or DEFAULT_DOMAIN_ROLES)
        self.ips = ips or IPv4AddressSet(network = self)
        self.nodes = nodes or NodeSet(network = self)
        
        self.locator = helpers.Locator()
        self.writer = helpers.PSMLWriter()
        self.cache = set()

    ## Adding refs

    def addRef(self, object: base.NetworkObject, ref: str) -> None:
        """
        Adds a pointer from *ref* to *object* as long as it is present in the network.

        :param object: The object to point *ref* to.
        :type object: base.NetworkObject
        :param ref: The identifier which can now be used to find *object*.
        :type ref: str
        :raises TypeError: If *object* is of an incompatible type.
        :raises AttributeError: If *object*'s ``network`` attribute is not this network.
        """
        if object.network is self:
            if isinstance(object, nwobjs.Domain):
                self.domains[ref] = object
            elif isinstance(object, nwobjs.IPv4Address):
                self.ips[ref] = object
            elif isinstance(object, nwobjs.Node):
                self.nodes[ref] = object
            else:
                raise TypeError(f'Cannot add ref to object of type {type(object)}')
        else:
            AttributeError('Cannot add ref to object when it is part of a different network.')

    def createNoderefs(self, node_identity: str, dnsobj_name: str, cache: set[str] = None) -> None:
        """
        Creates noderefs from the DNSObj at *dnsobj_name* (and DNSObjs which resolve to it) to the node with *node_identity*.

        :param node_identity: The identity of the target node.
        :type node_identity: str
        :param dnsobj_name: The name of the DNSObj to link from.
        :type dnsobj_name: str
        """
        node = self.nodes[node_identity]
        if not cache:
            cache = set()
        elif dnsobj_name in cache:
            return cache
        cache.add(dnsobj_name)

        if dnsobj_name in self.ips:
            dnsobj = self.ips[dnsobj_name]
            dnsobj_set = node.ips

        elif dnsobj_name in self.domains:
            dnsobj = self.domains[dnsobj_name]
            dnsobj_set = node.domains
        
        else: return cache

        if dnsobj.node:
            if isinstance(dnsobj.node, nwobjs.PlaceholderNode):
                assert dnsobj.node is not node, \
                    'Trying to replace placeholder node with itself.'
                self.nodes.consumePlaceholder(dnsobj.node, node)
            return cache

        elif dnsobj.node: return

        dnsobj_set.add(dnsobj.name)
        dnsobj.node = node
        
        for backrefs in dnsobj.backrefs.values():
            for backref in backrefs:
                cache |= self.createNoderefs(node_identity, backref, cache)

        if hasattr(dnsobj, 'nat') and dnsobj.nat:
            cache |= self.createNoderefs(node_identity, dnsobj.nat, cache)

        return cache

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

    def setToPSML(self, set: str) -> None:
        """
        Serialises a NetworkObjectContainer to PSML and writes the PSML files to *dir*.

        :param set: The atribute name of the set to serialise, one of: 'domains', 'ips', or 'nodes'.
        :type set: str
        """
        self.writer.serialiseSet(getattr(self, set))

    def writePSML(self) -> None:
        """
        Writes the domains, ips, and nodes of a network to PSML using ``self.writer``.
        """
        self.setToPSML('domains')
        self.setToPSML('ips')
        self.setToPSML('nodes')
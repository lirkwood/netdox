"""
This module contains the NetworkObject classes used to store the DNS and Node information, their containers, and two helper classes.

The NetworkObject class is an abstract base class subclassed by Domain, IPv4Address, and Node. 
NetworkObjects represent one type of object in the network. 
It could be a unique FQDN found in a managed DNS zone, an IP address one of those domains resolves to, or a Node.
A Node is representative of a single machine / virtualised machine.
When writing plugins for the node stage developers are encouraged to write their own subclass of Node, 
specific to the target of their plugin.
This allows you to define how the Node will behave when it is added to a NodeSet or Network, 
and it's strategy for merging with other Nodes.
"""

import base, containers, helpers
from objects import *
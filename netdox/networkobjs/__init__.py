"""
This module contains the NetworkObject classes used to store the DNS and Node information, their containers, and two helper classes.

The NetworkObject class is an abstract base class representing one instance of one type of object in the network. 
All NetworkObjects currently implemented can be further categorised into DNSObjects and Nodes.
DNSObjects represent the endpoints for DNS records: either a FQDN (Domain) or an IPv4 address.
A Node is representative of a single machine / virtualised machine.
DefaultNode is an implementation of Node which has exactly one private IPv4 address (and any number of public IPv4s).
This may be useful for plugin writers who do not want to implement the whole Node class.
"""

import base, containers, helpers
from objects import *
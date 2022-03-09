.. _dev:

Developing for Netdox
#####################

Architecture
============
The primary objects in Netdox are DNS objects, Nodes and their containing Network. 
DNS objects (domains and IPv4 addresses) represent a single, unique name in the DNS.
These objects are the primary anchors for the documentation, and are likely what you will find yourself searching for when trying to diagnose an issue using Netdox.

Nodes represent a single (physical or virtualised) machine; In other words, a significant endpoint for a DNS record.
For example, the XenOrchestra plugin will connect to your XenOrchestra instance and retrieve any running VMs. 
It then provides VirtualMachine nodes to the Network object, which will decide which DNS objects resolve to it based on information from XenOrchestra aswell as any other enabled plugins.

Plugins also have the opportunity to generate additional documentation to provide extra context or information. 
In the case of XenOrchestra, a PageSeeder publication is generated which allows you to walk through the hierarchy of organisational units that XO defines and easily see their relationship to each other,
from individual VMs, to the host machines and the VMs running on them, to the pools the hosts belong to.

Plugins
=======
Developing plugins for Netdox is extremely simple. 
No configuration is required in Netdox beyond adding the name of the package to a whitelist. 
Everything else can be done from within your python code.
Each plugin should be a python package in the ``netdox.plugins`` namespace package, 
and will be loaded and run at the correct stage automatically.
More detail is available here: :ref:`plugins`.
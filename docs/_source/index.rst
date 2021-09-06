.. _about:

About
#####

Netdox Overview
===============
Netdox is a highly modular Python 3 application that generates network documentation in PageSeeder markup language (PSML) for display by PageSeeder.
The objective of Netdox is to improve the productivity of network administrators by consolidating information from a range of systems.
This reduces the need for administrators to move between many different interfaces, and minimises the familiarity required with each service.
The documentation is updated and pruned daily to keep data current and accurate, and can be refreshed at any time. 
Moreover, any changes are preserved in comprehensive versions provided by PageSeeder's document history functionality.

Netdox leverages plugins to retrieve data from the services in *your* environment.
This allows you to effectively provide your network administrators with a one-stop shop for querying the state of the network.
This combined with the XRef links between the documents results in a highly connected and transparent visualisation of your network.

Using Netdox
------------
Quick setup guide can be found here: :ref:`quickstart`.
More detail on how to correctly configure Netdox is available here: :ref:`config`.

Architecture
------------
The primary objects in Netdox are DNS objects, Nodes and their containing Network. 
DNS objects (domains and IPv4 addresses) represent a single, unique name in the DNS.
These objects are the primary anchors for the documentation, and are likely what you will find yourself searching for when trying to diagnose an issue.

Nodes represent a single (physical or virtualised) machine; In other words, a significant endpoint for a DNS record.
For example, the XenOrchestra plugin will connect to your XenOrchestra instance and retrieve any running VMs. 
It then provides VirtualMachine nodes to the Network object, which will serialise them to PSML and upload them during a refresh.

Plugins also have the opportunity to generate additional documentation to provide extra context or information. 
In the case of XenOrchestra, 
a PageSeeder publication is generated which allows you to walk through the hierarchy of objects and easily see their relationship to each other,
from pools to hosts to VMs.

However the uses for Netdox go beyond simple documentation generation. 
Plugins in Netdox are able to respond to *webhooks* sent by PageSeeder when a document is updated, 
meaning you are able to use the documentation to trigger automation tools such as Ansible, modify your DNS, alert your network admins, etc.
More information available here: :ref:`webhooks`.


Development
===========
Developing plugins for Netdox is extremely simple. 
No configuration is required in Netdox beyond adding the name of the package to a whitelist. 
Everything else can be done from within your python code.
Each plugin should be a python package in the ``netdox.plugins`` namespace package, 
and will be loaded and run at the correct stage automatically.
More detail is available here: :ref:`plugins`.

.. toctree::
   :maxdepth: 4

   config.rst
   webhooks.rst
   plugins.rst
   source.rst
   releases.rst
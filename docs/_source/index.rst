.. _index:

Dev
===

Netdox Overview
---------------
The following pages are for developers that need to maintain or extend Netdox, an application that generates network documentation in PageSeeder markup language (PSML) for display by PageSeeder.

Netdox is a highly modular, containerised application built with primarily with Python (although it utilises Java and Node.js for certain tasks).
The objective of Netdox is to improve the productivity of network administrators by consolidating information from a range of systems.
This reduces the need for administrators to move between many different interfaces, and minimises the familiarity required with each service.
The documentation is updated and pruned daily to keep data current and accurate, and can be refreshed at any time.

Plugins used in the Allette instance of Netdox interface with the following services:

- ActiveDirectory
- DNSMadeEasy
- CloudFlare
- Xen Orchestra
- Kubernetes
- AWS EC2
- Icinga
- Ansible
- FortiGate
- pfSense

Architecture
------------
Netdox is, at it's simplest, a DNS record aggregator.
All other functionality simply extends Netdox's ability to define network nodes by the DNS records that reference them.
A core concept that Netdox leverages to deduce the topology of a network is that IP addresses are both immutable and permanent.
More IP addresses cannot be created in an existing address space, and a single IP address always represents a single node on the network.
This provides Netdox with an anchor that can be used to identify a node's position and role in the network's ecosystem.

As IP addresses are deployed, released and redeployed, all changes are captured in PageSeeder through the document history.
This can help to identify the cause of a problem, or even resolve one before it arises.
Furthermore, this tracking of IP address usage means it is trivial to capture the next unused address for use within other automated services.

Objects and their meaning
-------------------------
The most important objects in Netdox are the NetworkObjects and their containers.
There are three subclasses of NetworkObject in the core code; The Domain, IPv4Address, and Node objects.
Domain and IPv4Address are both containers for DNS records with the same name. For example, a Domain with the name 'netdox.allette.com.au' contains all the A and CNAME DNS records which have that name.
For more details on how these classes can be used / extended, see :ref:`networkobjs` and :ref:`plugins`.


.. toctree::
   :maxdepth: 1

   config.rst
   utils.rst
   plugins.rst
   refresh.rst
   webhooks.rst
   security.rst
   files.rst
   releases.rst
.. _config:

Configuring Netdox
==================

Most of the configuration for Netdox is done through PageSeeder, but any plugin settings must be set through the file ``config.json`` (a template is available in the root of the git repository). 
There are also two additional recognised configuration files, ``locations.json`` and ``roles.json``. 
These files allow you to assign locations to IP address ranges and override the DNS role for a domain respectively (for more see :ref:`locations` and :ref:`roles`).
The files are stored in the ``cfg`` directory in persistent storage, but ``config.json`` is encrypted (see :ref:`security`) and its contents are available through the ``utils.auth`` function (for more see :ref:`utils`).

The main config file on PageSeeder (path: ``config/config.psml``  docid: ``_nd_config``) configures the exclusion list aswell as DNS roles.
In order to add a domain to the exclusion list, and therefore remove it entirely from Netdox and ignore it wherever it may appear, simply add it to the *exclude* fragment in a line on its own.


.. _locations:

Location data
-------------

Location data is an optional part of Netdox, but it provides some additional clarity for networks which span multiple physical locations.
The configuration is done through the ``locations.json`` file (stored in persistent storage as mentioned above). 
Each location should be defined by an array of IPv4 subnets using the *CIDR* notation (e.g. ``192.168.0.0/16``). 
The smallest subnet an IP is part of will be used to define that IP's location, so that you don't have to define a location for every possible subnet in your network.

A conveniece function exists for this so that you can use location data in plugins, see :ref:`utils`.


.. _roles:

DNS roles
---------

The purpose of DNS roles is to allow additional configuration of Netdox on a per-domain basis through user-friendly PageSeeder documents.
This is done by setting properties in the role definition (a dns_role document in PageSeeder with a docid matching ``_nd_role_*``). 
By default the only properties are name and description fields, and a screenshot property which tells Netdox whether or not to attempt to screenshot the websites hosted on the domain with said role. 
By default the roles included are: default, website, pageseeder.

Once you have created any additional roles, you must tell Netdox about them. In order to do this, use the config file (located in ``config/config.psml`` from the upload context) and create an xref in the roles fragment to your role document. 
By convention any additional role definitions are placed in this config directory aswell.

In order to assign a role to a given domain, you simply set the *role* property to an xref to the desired role document. 
Alternatively, you may set roles in the ``roles.json`` config file (for more see :ref:`config`)
.. _config:

Configuring Netdox
##################

.. _localconf:

Local configuration
===================
All local config files are JSON files, and should be placed in the ``src/`` directory.
Templates are available in the ``src/defaults/localconf`` directory.

The primary configuration file in Netdox is an encrypted JSON file used to hold the authentication details for the attached PageSeeder instance, 
aswell as any config values required by the plugins you wish to use. 
Each plugin needs different configuration values, but they should be documented in the readme included with each plugin.
The object should be placed in the ``plugins`` object under the name of the plugin.

In order to load this file into netdox you should use the ``config`` method in the executable.
This will encrypt the file, move it to the correct location and test the connection to PageSeeder using that config.
If this test succeeds the original will be deleted. 
Should you want to modify the config, you should use the ``decrypt`` method to retrieve it.


.. _locations:

Location data
-------------

Location data is an optional part of Netdox, but it provides some additional clarity for networks which span multiple physical locations.
Each location should be defined by an array of IPv4 subnets using the *CIDR* notation (e.g. ``192.168.0.0/16``) in the ``locations.json`` file.
The name of the array will be the canonical name for that location. 
The smallest subnet an IP is part of will be used to define that IP's location, so that you don't have to define a location for every possible subnet in your network.


.. _roles:

DNS roles
---------

The purpose of DNS roles is to allow additional configuration of Netdox on a per-domain basis through user-friendly PageSeeder documents.
This is done using the ``dns_role`` document type, a template of which is available in the root of the project.
The format of these documents is actually relatively flexible, and can be modified to provide configuration to plugins as well.
For example, the screenshot property, which is included by default in the template, 
takes a boolean value which tells Netdox whether or not to attempt to navigate to that domain and screenshot it.
The roles that are included with the base installation (and the ones that will be uploaded to PageSeeder if none are present)

Once you have created any additional roles, you must tell Netdox about them. In order to do this, use the config file (located in ``config/config.psml`` from the upload context) and create an xref in the roles fragment to your role document. 
By convention any additional role definitions are placed in this config directory aswell.

In order to assign a role to a given domain, you simply set the *role* property to an xref to the desired role document. 
Alternatively, you may set roles in the ``roles.json`` config file (for more see :ref:`config`)

.. _psconf:

PageSeeder Configuration
========================
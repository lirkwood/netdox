.. _config:

Configuring Netdox
##################

.. _localconf:

Local configuration
===================

Config location
---------------
After initialising a configuration directory using ``netdox init <path>``, 
a collection of templates for config files will be copied there for you to populate.
Most of the configuration for Netdox lives in one file; It's template will be named ``config.json``.
It should, when populated, contain all the configuration values for connecting to your PageSeeder instance.
In addition, this file should contain any values required by your enabled plugins, 
in an object in the *plugins* dictionary (with the plugin name in lower case as the key). 
Each plugin should document the JSON object it expects, usually in the ``README.md``.

This file will be encrypted when you load it into Netdox, and the unencrypted original deleted automatically. 
For more information about loading the config, use the CLI help (``netdox -h``, ``netdox config -h``).

.. _locations:

Location data
-------------

Location data is an optional part of Netdox, but it provides some additional clarity for networks which span multiple physical locations.
Each location should be defined by an array of IPv4 subnets using the *CIDR* notation (e.g. ``192.168.0.0/16``) in the ``locations.json`` file.
The key of the array will be the canonical name for that location, and will appear in the documents etc.
The smallest defined subnet an IP is part of will be used to select that IP's location, 
so that you don't have to define a location for every possible subnet in your network.

.. _roles:

Domain roles
------------

Domain roles, like location data (see above), are optional. 
Their purpose is to provide a native interface to specify settings to plugins, on a domain-by-domain basis.
Each role defines an arbitrary number or properties to propagate to any domain which has been assigned the role.
For example, the screenshot property tells the *screenshots* plugin whether or not to attempt to take a screenshot of domains with that role.

In the ``roles.json`` template, you will see just two roles defined: *exclusions* and *default*.
Default is simply an empty role, and you may modify it as you please. 
However be aware, any domains with no assigned role will be assigned this role instead.
The exclusions role is baked in, and any domains assigned to it will be immediately discarded. 
These domains will not appear anywhere in the generated documentation, 
and will not be added to the Network object in the code.

You may create as many roles as you like, as long as they have unique names.
Each role should at least have a ``domains`` property, which must be an array of FQDNs to apply the role to.

.. _enabled_plugins:

Enabled Plugins
---------------

Plugins are disabled by default and will not run automatically just because they're installed.
In order to enable a plugin, add its name to the array in ``plugins.json``.
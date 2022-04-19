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
In addition, this file should contain any values required by your enabled plugins. 
Place them in an object in the *plugins* dictionary (with the plugin name in lower case as the key).
Each plugin should document the JSON object it expects, usually in the ``README.md``.

This file will be encrypted when you load it into Netdox, and the unencrypted original deleted automatically. 
For more information about loading the config, use the CLI help (``netdox -h``, ``netdox config -h``).

There is additional configuration available on a per-NetworkObject basis, using document labels in PageSeeder.
For more, see below.

.. _locations:

Location data
-------------

Location data is an optional part of Netdox, but it provides some additional clarity for networks which span multiple physical locations.
Each location should be defined by an array of IPv4 subnets using the *CIDR* notation (e.g. ``192.168.0.0/16``) in the ``locations.json`` file.
The key of the array will be the canonical name for that location, and will appear in the documents etc.
The smallest defined subnet an IP is part of will be used to select that IP's location, 
so that you don't have to define a location for every possible subnet in your network.

.. _enabled_plugins:

Enabled Plugins
---------------

Plugins are disabled by default and will not run automatically just because they're installed.
In order to enable a plugin, add its name to the array in ``plugins.json``.


.. _labels:

Document Label Attributes
-------------------------

Netdox allows you to leverage the batch application/removal of document labels to easily configure plugin-level attributes
on a document-by-document basis. For each label on a document, Netdox will look up the label name in the PageSeeder config file 
(file of type ``netdox`` with docid ``_nd_config``) and apply any attributes defined there to the object the document represents.

To use the config, create a document matching the stipulations above.
Each fragment you create in the labels section can be used to configure the attributes of a single document label.
Each property in the fragment is an attribute key/value pair.
If multiple labels on the same document provide conflicting values for an attribute, 
the value from the label that was defined first in the file will take precedence.

This document also has a section titled 'Exclusions'. Domains in this section will be completely ignored by Netdox.

Plugins can register attributes using an iterable of strings named ``__attrs__``, defined at the module level.
During a refresh, the template for the config file on PageSeeder will be updated, so that each new 'label' fragment created
contains a property for each attribute registered by a plugin. 
*Note*: There's no need to recreate your config file if the registered attributes have changed —
a new config file will be uploaded with the correct structure, and all your old configuration will be preserved.
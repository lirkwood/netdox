.. _config:

Configuring Netdox
##################

.. _psconf:

PageSeeder Configuration
========================
Netdox reads configuration values from a PageSeeder document of type ``netdox`` and docid ``_nd_config`` before every refresh.
The template for this document is included in the source, and both the document type and document itself will be created on the PageSeeder server if they cannot be found.
The document consists of three sections, described below.

.. _labels:

Document Label Attributes
-------------------------
Section ID: ``labels``

Netdox allows you to leverage the batch application/removal of document labels to easily configure plugin-level attributes
on a document-by-document basis. For each label on a document, Netdox will look up the label name in the PageSeeder config file and apply any attributes defined there to the object the document represents.

Each fragment you create in the labels section can be used to configure the attributes of a single document label.
Each property in the fragment is an attribute key/value pair.
If multiple labels on the same document provide conflicting values for an attribute, 
the value from the label that was defined first in the file will take precedence.

Plugins tell Netdox which attributes they expect to be configured for a label.
During a refresh, the template for the config file on PageSeeder will be updated, so that each new 'label' fragment created contains a property for each attribute requested by a plugin. 
*Note*: There's no need to recreate your config file if you enabled or disable a plugin; a new config file will be uploaded with the correct structure, and all your old configuration values will be preserved.

.. _organizations:

Organization Labels
-------------------
Section ID: ``organizations``

This section allows you to associate an 'Organization' with a DNS object or node using document labels.
This is a simple way to provide another view on your network's domains, IPs, and nodes.
Each fragment specifies the name of the document label, and an XRef to a document that describes that organization.
The linked document may contain any content (or none if you desire), but each organization should have a unique document.

Any documents bearing a label that has an organization associated with it will be marked as part of that organization.
This will be extended to any documents which resolve to it, provided they do not already have an organization explicitly configured.

.. _exclusions:

Domain Exclusions
-----------------
Section ID: ``exclusions``

This document also has a section titled 'Exclusions'. Domains in this section will be completely ignored by Netdox.

.. _localconf:

Local configuration
===================

Netdox also reads more sensitive data from local files.

Config location
---------------
After initialising a configuration directory using ``netdox init <path>``, a collection of templates for config files will be copied there for you to populate.
Most of the configuration for Netdox lives in one file; Its template will be named ``config.json``.
It should, when populated, contain all the configuration values for connecting to your PageSeeder instance.

In addition, this template will contain the outline for configuring any installed plugins.
These sections should be completed for any plugins you intend to enable.
For more detail refer to the plugin README files, which will also be copied to the directory during initialisation.

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
Alternatively, if the array contains a single asterisk ("*"), all plugins will be enabled.
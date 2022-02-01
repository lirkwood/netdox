.. _plugins:

Plugins
#############

About Plugins
=============
Plugins allow Netdox to retrieve data from an arbitrary number of services or tools.
They are modules or packages placed in the ``netdox.plugins`` namespace, and will be called by Netdox at a series of hook points,
known as stages. These stages represent the logical stages within the core code, 
and you should restrict the functionality of each stage of your plugin to the purpose of the stage in order to avoid confusion about the state of the Network object.

- dns: Add DNS objects to the Network.
- nat: Add NAT / switch info to the DNS objects in the Network.
- nodes: Add Node objects to the Network. 
- footers: Add fragments to the footers of NetworkObjects in the Network.
- write: Writing PSML to disk for uploading to PageSeeder.
- cleanup: Cleanup to perform after the PSML has been uploaded.


Plugin Exports
==============
Certain variables, if defined at the top level of your plugin, can be used to control the behaviour of Netdox.
For example, in order to register your plugin for a stage, 
create a dictionary at the top level of your plugin called ``__stages__``.
In this dictionary the key of each item should be the name of the desired stage, 
and the value should be a callable object that takes a single Network object as a positional argument.

In order to register a label attribute, use the ``__attrs__`` name for an iterable object containing the
string names of the attributes to register. For more info see :ref:`config`.

To register a config object that your plugin will expect to read from the application config (``config.json``),
use a dictionary named ``__config__``. 
This dict will be copied to the config template when a new netdox instance is initialised, under the name of your plugin.

To register a Node type as an export from your plugin, use the ``__nodes__`` iterable.

To register your plugin as dependent on another Netdox plugin, add the plugin name to the ``__depends__`` iterable.


Default Plugins
===============
A number of plugins are installed with Netdox by default. The source code for these plugins is documented below.

.. toctree::
    :maxdepth: 4

    source/netdox.plugins.rst
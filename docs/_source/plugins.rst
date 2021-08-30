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

In order to register your plugin for a stage, create a dictionary at the top level of your plugin called ``__stages__``.
In this dictionary the key of each item should be the desired stage, 
and the value should be a callable object that takes a single Network object as a positional argument.

For more information about adding NetworkObjects to the Network, see :ref:`source`.


Default Plugins
===============
There are a number of plugins included in the installation by default, documented below.
Those that are untested or non-functional have been omitted.

.. toctree::
    :maxdepth: 4
 
    plugins/plugins.activedirectory
    plugins/plugins.aws
    plugins/plugins.cloudflare
    plugins/plugins.dnsmadeeasy
    plugins/plugins.fortigate
    plugins/plugins.hardware
    plugins/plugins.icinga
    plugins/plugins.k8s
    plugins/plugins.pfsense
    plugins/plugins.screenshots
    plugins/plugins.xenorchestra
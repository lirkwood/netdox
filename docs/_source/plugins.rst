.. _plugins:

About plugins
==============
Plugins provide instance-specific functionality to Netdox in order to support any network/environment.
Each plugin must be an importable Python module placed in a directory within the netdox/plugins folder, where the name of the directory is taken as the plugin name.


Plugin stages
-------------
Plugins may perform multiple different tasks, from gathering DNS data to setting monitors for any domains which satisfy certain requirements. Because of this, some plugins may need to be run in a specific order, or provided with certain information by other plugins. In order to allow plugin writers to specify when to run their module, the concept of stages was introduced.
Currently Netdox attempts to run any plugins in stages 'dns', 'resource', and 'other', in that order.

:dns:
    Plugins in the *dns* stage are intended to run first, and their main purpose is to retrieve DNS records from any provider or other source, and add them to the master set.

:resource:
    Plugins in the *resource* stage are run directly after the DNS stage, and are intended to retrieve information about any external resource that you wish to include in your network documentation. Two good examples are the default plugins 'kubernetes' and 'xenorchestra', which also generate their own psml.

:other:
    These plugins are run last, after some additional processing has been done on the data e.g. application of DNS roles (for more see :ref:`roles`)

In order to set the stage for a plugin simply expose a string named 'stage' with the value of the desired stage at the top level of the module.
Any plugins with no defined stage or a stage not mentioned above are not run automatically, but may be called by other plugins or triggered by webhooks (for more see :ref:`webhooks`)


Running plugins
---------------
Plugins have no mandatory attributes, but in order for Netdox to auto-run your plugin it must expose a function named 'runner' at the top level of the module.
This function will be called with two arguments, a forward and reverse DNS set.
These 'DNS sets' are typed like: 

``dict[str, utils.DNSRecord]`` and ``dict[str, utils.PTRRecord]``

where the dictionary keys are the record names (either domain or IPv4 address).

Any configuration values needed for your plugins to run should be placed in authentication.json (for more info see :ref:`config`).


pluginmaster
------------
.. automodule:: pluginmaster
    :members:
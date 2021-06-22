.. _plugins:

About plugins
==============
Plugins provide instance-specific functionality to Netdox in order to support any network/environment.
Each plugin must be an importable Python module placed in a directory within the netdox/plugins folder, where the name of the directory is taken as the plugin name.


Plugin stages
-------------
Plugins may perform multiple different tasks, from gathering DNS data to setting monitors for any domains which satisfy certain requirements. Because of this, some plugins may need to be run in a specific order, or provided with certain information by other plugins. In order to allow plugin writers to specify when to run their module, the concept of stages was introduced.
Currently Netdox attempts to run any plugins in stages 'dns', 'resource', 'pre-write', and 'post-write' in that order.

:dns:
    Plugins in the *dns* stage are intended to run first, and their main purpose is to retrieve DNS records from any provider or other source, and add them to the master set.

:resource:
    Plugins in the *resource* stage are run directly after the DNS stage, and are intended to retrieve information about any external resource that you wish to include in your network documentation.
    Two good examples are the default plugins 'kubernetes' and 'xenorchestra', which also generate their own psml.

:pre-write:
    These plugins are run before any PSML is generated, after some additional processing has been done on the data e.g. application of DNS roles (for more see :ref:`roles`)

:post-write:
    These plugins run after the main PSML generation has completed, and may modify the output documents or simply perform other actions which require the output documents to already exist.

In order to set the stage for a plugin simply expose a string named 'stage' with the value of the desired stage at the top level of the module.
Any plugins with no defined stage or a stage not mentioned above are not run automatically, but may be called by other plugins or triggered by webhooks (for more see :ref:`webhooks`)


Running plugins
---------------
Plugins have no mandatory attributes, but in order for Netdox to auto-run your plugin it must expose a function named 'runner' at the top level of the module.
This function will be called with two arguments, a forward and reverse DNS set (for more see :ref:`utils`)

Any configuration values needed for your plugins to run should be placed in authentication.json (for more see :ref:`config`).


pluginmanager
-------------

.. automodule:: plugins
    :members:


Default Plugins
===============

ActiveDirectory
---------------

.. automodule:: plugins.activedirectory
    :members:

.. automodule:: plugins.activedirectory.fetch
    :members:

.. automodule:: plugins.activedirectory.create
    :members:

DNSMadeEasy
-----------

.. automodule:: plugins.dnsmadeeasy
    :members:

.. automodule:: plugins.dnsmadeeasy.fetch
    :members:

.. automodule:: plugins.dnsmadeeasy.create
    :members:

CloudFlare
----------

.. automodule:: plugins.cloudflare
    :members:

.. automodule:: plugins.cloudflare.fetch
    :members:

NAT
---------------------------

.. automodule:: plugins.nat
    :members:

.. automodule:: plugins.nat.fetch
    :members:

Kubernetes
----------

.. automodule:: plugins.kubernetes
    :members:

.. automodule:: plugins.kubernetes.refresh
    :members:

.. automodule:: plugins.kubernetes.webhooks
    :members:

Xen Orchestra
-------------

.. automodule:: plugins.xenorchestra
    :members:

.. automodule:: plugins.xenorchestra.fetch
    :members:

.. automodule:: plugins.xenorchestra.create
    :members:

AWS
---

.. automodule:: plugins.aws
    :members:

Icinga
------

.. automodule:: plugins.icinga
    :members:

.. automodule:: plugins.icinga.api
    :members:
    
.. automodule:: plugins.icinga.ssh
    :members:
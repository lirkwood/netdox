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
These variables are listed and defined below.
``__stages__``
    (REQUIRED) A map linking ``netdox.app.LifecycleStage`` enum members to callable objects that take a single ``netdox.Network`` object.
    Each callable is the function or method to run for the indicated stage.
``__attrs__``
    (OPTIONAL) An iterable of strings.
    Each item is a field that will appear as configurable in the PageSeeder label config (:ref:`config`).
    Your plugin should handle the logic for acting on the value set in this field during a refresh.
``__config__``
    (OPTIONAL) A python dictionary serialisable to JSON.
    This object will be serialised to JSON and copied to the application config template when a new one is generated.
    It should provide the fields for any configuration that should be done on your plugin, 
    and sensible defaults where possible
``__nodes__``
    (OPTIONAL) An iterable of type objects.
    Iterable should contain every ``netdox.nodes.Node`` subclass your plugin includes in its output.
    This will be used for recreating a Network object from output format.
``__depends__``
    (OPTIONAL) An iterable of strings.
    Each item should be the name of a plugin that this plugin requires in order to run.
    Plugin will not run if there is an item in this iterable not matching the name of a running plugin.
``__output__``
    (OPTIONAL) An iterable of strings.
    Each item should be the name of a file or directory this plugin outputs too.
    This will be used to ensure the plugin output is included on the remote server, 
    and to allow Network recreation from output format.

For example, in order to register your plugin for a stage, 
create a dictionary at the top level of your plugin called ``__stages__``.
In this dictionary the key of each item should be the enum member of the desired stage, 
and the value should be a callable object that takes a single Network object as the argument..


Default Plugins
===============
A number of plugins are installed with Netdox by default. The source code for these plugins is documented below.

.. toctree::
    :maxdepth: 4

    source/netdox.plugins.rst
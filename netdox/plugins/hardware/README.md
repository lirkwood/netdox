### Node Plugin
---
# Hardware
## Configuring this plugin

This plugin reads PSML files from the `website/hardware/` directory on your PageSeeder instance.
These files do not need to follow a specific template, although an example is provided in the `templates/` directory at the root of the Netdox project.
Whatever template you use, only properties fragments in the section with an ID of `info` will be considered by this plugin. 

The section will be searched for two properties, *name* and *ipv4*. If these two properties are both present, and the content of *ipv4* is a valid IPv4 address, a the contents of the entire section will be copied to a Node with that IP address.

The files in the hardware directory will not be modifed by Netdox.

As a node plugin, it should be listed in the *nodes* array in `pluginconf.json`.
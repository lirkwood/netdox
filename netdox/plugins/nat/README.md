### DNS Plugin
---
# NAT

This plugin has the functionality to gather NAT data from two sources:

- pfSense: A Node.js / puppeteer script which scrapes NAT information from a pfSense web interface.
- Fortigate: Intended to use the fortigate api, however this remains unimplemented. In its current state the data is just read from a text file in the `netdox/src/` directory at the root of the project.

## Configuring this plugin

This plugin expects three key/value pairs in `config.json`.

- **username**: The username to use to log into pfSense.
- **password**: The password to use to log into pfSense.
- **host**: The FQDN of your pfSense instance.

As a dns plugin, it hsould be listed in the *dns* array in `pluginconf.json`.
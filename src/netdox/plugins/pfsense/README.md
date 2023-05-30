### NAT Plugin
---
# pfSense

This plugin uses pyppeteer to scrape 1:1 NAT information from the pfSense web interface.

## Configuring this plugin

This plugin expects 3 key/value pairs in `config.json`.

- **username**: The username to log into the web interface with.
- **password**: The password to pair with *username*.
- **host**: The FQDN of your pfSense instance.
- **browser**: Absolute path to browser executable to use during the scraping.

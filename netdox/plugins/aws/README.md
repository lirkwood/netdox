### Node Plugin
---
# AWS
## Configuring this plugin

This plugin requires three key/value pairs in `config.json`.

- **region**: The region your EC2 instance is running in.
- **aws_access_key_id**: Your AWS EC2 access key ID.
- **aws_access_secret_key**: Your AWS EC2 access secret key.

As a node plugin, it should be listed in the *nodes* array in `pluginconf.json`.
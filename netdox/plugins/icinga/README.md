### Post-write Plugin
---
# Icinga
## Configuring this plugin

This plugin expects key / map pair per instance of Icinga.
The key should be the fully qualified domain name of your instance, and the map should look like the one below:

```json
{
    "locations": [ "location1" ],
    "username": "your icinga api user's username",
    "password": "your icinga api user's password"
}
```

The locations array should be populated by your defined network locations as they appear in `locations.json`.

As a post-write plugin, it should be listed in the *post-write* array in `pluginconf.json`.
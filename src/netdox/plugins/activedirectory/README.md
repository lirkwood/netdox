### DNS Plugin
---
# ActiveDirectory

This plugin uses PowerShell Remoting to dump records from the ActiveDirectory DNS service.
The credentials provided in the config must be for a user and machine that has permission to perform a DNS zone transfer, and has the `DnsServer` module installed.
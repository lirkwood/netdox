.. _release-notes:

Releases
########

v1.0.1
======
Updated CI/CD and made all code mypy compliant.
* Added XOServer to the XenOrchestra plugin.
* Removed globals from multiple plugins, as mypy does not work well with them.
* Added generic types for NetworkObjectContainers.

v1.0.0
======
Replaced the roles system with configurable label attributes.
* Replaced roles system with a new config architecture based on document labels.
* Moved content of objs package into root package.
* Updated Icinga plugin to use the API instead of SSH.
* Made PSML classes more robust / flexible.

v0.1.0
======
Added certificates, snmp, daily report, and psml helper classes.
* Replaced the docid attribute on Node with a property that should transform the identity.
* Added PSMLLink and other functionality to psml module.
* Added certificates plugin.
* Added SNMP plugin.
* Added daily report.

v0.0.0
======
Initial release. Some parts of Netdox are still likely to change significantly.
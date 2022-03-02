.. _release-notes:

Releases
########

v1.3.3
======
Added validation, fixed loading zone issues, updated docs and search terms.

* Added docid length validation during serialisation.
* Updated IPv4Address search terms to use better tokens.
* Added Schematron validation for updated search terms.
* Refresh now clears the loading zone during initialisation.

v1.3.2
======
Bugfixes, refactors, updated search terms for IPv4s, updated dev scripts.

* Fixed some bugs when initialising the config dir / loading the config for the first time.
* Fixed icinga not recognising monitors as valid.
* NetworkManager now uses more efficient dependency evaluation logic.
* Fixed k8s plugin throwing exception if pod has no labels.
* Refactored multiple methods to have lower complexity.

v1.3.1
======
Bugfixes, added warning logs to report, add universal link method.

* Fixed Docker image crashing due to bug with copying plugin READMEs.
* Fixed Network cache containing all domains, breaking resolveTo.
* Added a fragment to daily report with warning+ level logs from the refresh.
* Added a link method to Network for a more uniform interface and better exclusion handling.
* Moved to using psml Section in place of a list of bs4 Tags for node psmlBody.
* Fixed bug in icinga plugin where locating a domain could recurse infinitely.
* Changed the default plugin whitelist to wildcard from empty.
* Fixed incorrect PSMLElement syntax in many places.

v1.3.0
======
Added Plugin dependencies, NodeProxy/ProxiedNode, DNSRecord, ps_k8s plugin.

* Plugins can now use the name __depends__ to register a list of plugin names the plugin depends on to run.
* Added NodeProxy and ProxiedNode to represent a proxy in front of a node, and a node behind a proxy respectively.
* Added DNSRecord/DNSRecordSet classes to better encapsulate records.
* Added ps_k8s plugin for discovering PageSeeder-based apps running on K8s.
* Added Section class to PSML module.
* PSML objects now proxy a BS4 Tag instead of subclassing.
* Initialising a config directory now copies plugin README files to the dir.
* Search terms are now configurable by the NWObj implementation.


v1.2.0
======
Added Organizations, PlantUML plugin, dynamic config templates.

* Added PluginWhitelist.
* Overhauled internal DNS system, replaced RecordSet with DNSRecordSet and DNSRecord.
* Config file now reads the __config__ attribute on plugins to generate template.
* Added support for multi-value psml Property.
* Added tldextract dependency to better validate DNS zones.

v1.1.0
======
Added docker image support, moved serialisation into NetworkObjects.

* Removed PSMLWriter, populate.
* Added dev scripts.
* Fixed DNS Zone property not being populated.
* Fixed config not setting its docid.

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
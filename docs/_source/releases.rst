.. _release-notes:

Releases
########

.. _v1_6_0:
v1.6.0
======
Made PlantUML diagrams more accessible, added report on dangling DNS records.

* PlantUML diagrams are now written to disk as SVG and uploaded in package.
* Diagrams are now included in documents rather than linked to.
* Added a report section for DNS records which are missing their reciprocal record.
* Hardened XenOrchestra plugin and stopped writing it's report if there is nothing new.

.. _v1_5_0:
v1.5.0
======
Added notes, moved away from placeholder node.

* No longer using placeholder node where it is possible to avoid it due to large numbers of duplicate documents.
* Updated placeholder node identity logic to increase collisions.
* Added the notes section which contains a fragment of persistent content.
* Added counted facets for debugging and sanity checks.

.. _v1_4_0:
v1.4.0
======
Generalised DNS, AWS overhaul, added recreating Network from psml, added persistent notes.

* Now support TXT DNS records.
* AWS now includes billing, volume and snapshot data.
* AWS instance names are now correctly set.
* Can now recreate Network from directory of PSML exported from PageSeeder (not all node types working yet.)
* Added notes concept; each network object has fragment with single para. Changes made here persist.

.. _v1_3_3:
v1.3.3
======
Added validation, fixed loading zone issues, updated docs and search terms.

* Added docid length validation during serialisation.
* Updated IPv4Address search terms to use better tokens.
* Added Schematron validation for updated search terms.
* Refresh now clears the loading zone during initialisation.

.. _v1_3_2:
v1.3.2
======
Bugfixes, refactors, updated search terms for IPv4s, updated dev scripts.

* Fixed some bugs when initialising the config dir / loading the config for the first time.
* Fixed icinga not recognising monitors as valid.
* NetworkManager now uses more efficient dependency evaluation logic.
* Fixed k8s plugin throwing exception if pod has no labels.
* Refactored multiple methods to have lower complexity.

.. _v1_3_1:
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

.. _v1_3_0:
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

.. _v1_2_0:
v1.2.0
======
Added Organizations, PlantUML plugin, dynamic config templates.

* Added PluginWhitelist.
* Overhauled internal DNS system, replaced RecordSet with DNSRecordSet and DNSRecord.
* Config file now reads the __config__ attribute on plugins to generate template.
* Added support for multi-value psml Property.
* Added tldextract dependency to better validate DNS zones.

.. _v1_1_0:
v1.1.0
======
Added docker image support, moved serialisation into NetworkObjects.

* Removed PSMLWriter, populate.
* Added dev scripts.
* Fixed DNS Zone property not being populated.
* Fixed config not setting its docid.

.. _v1_0_1:
v1.0.1
======
Updated CI/CD and made all code mypy compliant.

* Added XOServer to the XenOrchestra plugin.
* Removed globals from multiple plugins, as mypy does not work well with them.
* Added generic types for NetworkObjectContainers.

.. _v1_0_0:
v1.0.0
======
Replaced the roles system with configurable label attributes.

* Replaced roles system with a new config architecture based on document labels.
* Moved content of objs package into root package.
* Updated Icinga plugin to use the API instead of SSH.
* Made PSML classes more robust / flexible.

.. _v0_1_0:
v0.1.0
======
Added certificates, snmp, daily report, and psml helper classes.

* Replaced the docid attribute on Node with a property that should transform the identity.
* Added PSMLLink and other functionality to psml module.
* Added certificates plugin.
* Added SNMP plugin.
* Added daily report.

.. _v0_0_0:
v0.0.0
======
Initial release. Some parts of Netdox are still likely to change significantly.
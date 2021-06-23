.. _releases:

Releases
========

v1.2
---

- Added the DNSSet class as a container for DNSRecord/PTRRecords
- Added the pluginmanager class to make plugin interactions more efficient
- ``netdox start`` now only calls serve after successful initialisation
- Updated urimap (finally instnace independent)
- Added performing plugin actions in response to webhooks using the ``webhooks.json`` config file
- Added creating Simple site apps from Netdox documents using webhook actions
- Normalised filenames and serialised DNS sets are now ``forward.json`` and ``reverse.json`` respectively.

v1.1
---

- Added PageSeeder document templates to the root of the project for default document types and those introduced by stock plugins.
- Fixed the *for-search* property not being populated.
- Fixed broken links to screenshots of websites.
- Renamed the PageSeeder API script from ``ps_api`` to ``pageseeder``.
- Added function to load locations to ``utils``.
- Added support for webhook actions on non-standard document types.
- Updated to Puppeteer 10.0.0.
- Moved Icinga fragment into plugin-managed code.
- Replaced *other* plugin stage with *pre-write* and *post-write*.
- Removed *critical* decorator from ``utils``.
- Added creating Berlioz Simple Sites from webhooks to the ``kubernetes`` plugin.


v1.0
---

Initial stable release of Netdox
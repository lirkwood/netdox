.. _releases:

Releases
========

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
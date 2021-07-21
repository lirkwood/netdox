.. _files:

Source Code
===========

This is a full description of the Netdox source code, file-by-file.


.. _file_cleanup:

Cleanup
-------
`cleanup.py <https://gitlab.allette.com.au/allette/devops/network-documentation/-/tree/master/netdox/cleanup.py>`_

.. automodule:: cleanup
    :members:


.. _file_crypto:

Crypto
------
`crypto.sh <https://gitlab.allette.com.au/allette/devops/network-documentation/-/tree/master/netdox/crypto.sh>`_

Encrypts and decrypts files using the same cipher and key used throughout Netdox, for convenience and consistency.


.. _file_dns:

DNS
---
`dns.xsl <https://gitlab.allette.com.au/allette/devops/network-documentation/-/tree/master/netdox/dns.xsl>`_

Takes json dictionary of serialised DNS records as input, and writes out PSML documents.


.. _file_init:

Init
----
`init.py <https://gitlab.allette.com.au/allette/devops/network-documentation/-/tree/master/netdox/init.py>`_

.. automodule:: init
    :members:


.. _file_ips:

IPs
---
`ips.xsl <https://gitlab.allette.com.au/allette/devops/network-documentation/-/tree/master/netdox/ips.xsl>`_

Takes json dictionary of serialised PTR records as input, and writes out PSML documents.


.. _file_netdox:

Netdox
------
`netdox <https://gitlab.allette.com.au/allette/devops/network-documentation/-/tree/master/netdox/netdox>`_

The main executable. Has methods 'init', 'refresh', 'serve', and 'start'.

:Init:
    Copies files from persistent storage, decrypts sensitive files, and runs python initialisation.

:Refresh:
    Runs ``refresh.py`` and uploads to PageSeeder if successful. Logs are saved to ``/var/log/refresh-<date>.log``.

:Serve:
    Runs ``serve.py`` 

:Start:
    Runs *init*, then *refresh* and *serve*.


.. _file_pluginmaster:

Pluginmaster
------------
`pluginmaster.py <https://gitlab.allette.com.au/allette/devops/network-documentation/-/tree/master/netdox/pluginmaster.py>`_

:ref:`plugins`


.. _file_ps_api:

PageSeeder API
--------------
`pageseeder.py <https://gitlab.allette.com.au/allette/devops/network-documentation/-/tree/master/netdox/pageseeder.py>`_

.. automodule:: pageseeder
    :members:
    :exclude-members: auth

    .. autodecorator:: pageseeder.auth


.. _file_refresh:

Refresh
-------
`refresh.py <https://gitlab.allette.com.au/allette/devops/network-documentation/-/tree/master/netdox/refresh.py>`_

.. automodule:: refresh
    :members:


.. _file_screenshot:

Screenshot Compare
------------------
`screenshotCompare.js <https://gitlab.allette.com.au/allette/devops/network-documentation/-/tree/master/netdox/screenshotCompare.js>`_

Screenshots every website with the correct role (see :ref:`roles`) using Puppeteer.
Upon successful screenshot, the previous screenshot is fetched from persistent storage and compared using *img-diff-js*.
If the two images are significantly different (>= 10% of pixels) the domain is marked for review in the status update.


.. _file_serve:

Serve
-----
`serve.py <https://gitlab.allette.com.au/allette/devops/network-documentation/-/tree/master/netdox/serve.py>`_

.. automodule:: serve
    :members:


.. _file_status:

Status
------
`status.xsl <https://gitlab.allette.com.au/allette/devops/network-documentation/-/tree/master/netdox/status.xsl>`_
Takes json input and generates a daily 'Status Update' of the domains which may require human attention, 
e.g. a website which looks notably different or one which Netdox was unable to screenshot.


.. _file_utils:

Utils
-----
`utils.py <https://gitlab.allette.com.au/allette/devops/network-documentation/-/tree/master/netdox/utils.py>`_

:ref:`utils`
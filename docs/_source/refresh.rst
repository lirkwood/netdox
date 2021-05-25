.. _refresh:

Refreshing the DNS data
=======================

Each time the DNS data is to be refreshed, some configuration is first loaded from PageSeeder (see :ref:`config`) and plugins are discovered and initialised again (see :ref:`plugins`).

Once this has been done, any plugins in the *dns* stage are run, and immediately afterwards so are any *resource* plugins.
Some additional processing is performed on the DNS data at this point, such as applying DNS roles (for more see :ref:`roles`) or linking PageSeeder licenses to domains with the *pageseeder* role. 

After these processes are finished, the *other* plugin stage is executed, and screenshots are taken of any configured sites. Finally, some cleanup of the files on PageSeeder is performed, the PSML files are written to the ``out`` directory and zipped, and an ANT task is started to upload the zip to your configured PageSeeder server.

**expand**

.. _cleanup:

Cleanup
-------

When documents on PageSeeder become stale (represent records or domains that no longer exist in the DNS) they are sentenced by Netdox. 
This means a document label matching ``expires-YYYY-MM-DD`` will be applied, with the date being the current date plus thirty days. 
Should a document exist with a sentence date of either the current day or one which has passed, the document will be archived. 
Alternatively, should the record the document describes be created again, the document will simply be overwritten and the label removed.

During this time, should Netdox fail to screenshot any of the configured websites, a placeholder image is generated in place (if there is not already a screenshot of that site on PageSeeder).
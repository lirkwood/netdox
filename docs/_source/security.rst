.. _security:

Security
========

Netdox reads most of its sensitive information from ``config.json`` (see :ref:`config`).
This file is expected to be encrypted using the AES-256-CBC standard.
The initialisation vector is the hexdump of the string *authivpassphrase* and the key is expected in the environment variable *OPENSSL_KEY*.
Other files may be encrypted or decrypted using the ``crypto`` bash script for convenience.
It is recommended to encrypt at least any DNS data stored on disk.
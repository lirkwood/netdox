.. Netdox documentation master file, created by
   sphinx-quickstart on Mon May 24 17:19:19 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Documentation for the Netdox project
====================================

Netdox is a network documentation generator designed for use with PageSeeder.
It runs as a containerised application using mostly Python and XSLT but also some Node.js.
The main goal of Netdox is to make network administration less confusing and more efficient. 
By leveraging a plugin system, Netdox is able to integrate not only with whatever DNS provider you happen to use, but also with other frameworks which manage things such as VMs or Kubelets that are useful to document in the context of your network. 
Netdox then generates PSML documents and uploads them (along with any plugin-generated psml) to a configured PageSeeder server.



.. toctree::
   :maxdepth: 2
   :caption: Contents:

   config.rst
   plugins.rst
   refresh.rst
   webhooks.rst
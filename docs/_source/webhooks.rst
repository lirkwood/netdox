.. _webhooks:

Webhooks
========

Webhooks are used to perform actions on the DNS (or any other resource Netdox may be able to modify using plugins) based on documents on PageSeeder. 
When an event occurs on PageSeeder (most notably a workflow change) a HTTP POST request is sent to Netdox through the PageSeeder webhooks service. 
If this event is in fact a workflow change, and the new workflow is *Approved*, then the document is considered to describe the desired state of the DNS. 
In other words, any records in that document that do not already exist will be created. 

Netdox achieves this by reading the *source* property of each destination fragment. 
This value must match the name of a plugin (case insensitive) with a valid function or the record will not be created. Expected function names are ``create_A``, ``create_CNAME``, and ``create_PTR``. 
These functions must be exposed at the top level of the plugin module in order for Netdox to recognise them, and must take the following arguments:

create_A / create_CNAME:
    :name: A string containing the name to be used for the DNS record.

    :value: A string containing the value of the record (an IP address or FQDN, depending on the record type)

    :zone: A string containing the DNS zone the record should be created in.

create_PTR:
    :ip: A string containing the full IP address to use as the name of the PTR record.
    
    :value: A string containing the FQDN the PTR record should resolve to.

Modifying resources other than DNS has not yet been implemented.
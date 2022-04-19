.. _webhooks:

Webhooks
########

Webhooks are used to perform actions on any resource Netdox may be able to modify using plugins,
based on documents on PageSeeder. 
When an event occurs on PageSeeder (usually a workflow change) a POST request is sent to Netdox through the PageSeeder webhooks service. 
If this event is in fact a workflow change, and the new workflow is *Approved*, then the document is considered to describe the desired state of the network.

*to be expanded*
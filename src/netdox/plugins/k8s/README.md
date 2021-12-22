### Node Plugin
---
# Kubernetes
## Configuring this plugin

This plugin expects one key / map pair for each cluster.
The key should be the name of the cluster (must be valid against [a-zA-Z0-9_-]). The map should look as below:

```json
{
    "location": "Optional location to associate with the cluster",
    "host": "fqdn of your kubernetes api host",
    "clusterId": "The ID of your cluster",
    "projectId": "The ID of the project your cluster is in",
    "token": "Your kubernetes api access token"
}
```
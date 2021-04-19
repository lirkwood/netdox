#!/bin/bash
resource=$1
options=$2
echo "[INFO][k8s_fetch.sh] Fetching Kubernetes $resource..."
contexts=($(kubectl config get-clusters | tail -n +2))

json='{'
for context in ${contexts[@]}
do
    kubectl config use-context $context
    json+="\"$context\": $(kubectl get $resource $options -o json),"
done
json=${json%,}
json+='}'

echo $json > "src/$resource.json"

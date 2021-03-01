#!/bin/bash
resource=$1
echo "[INFO][k8s_fetch.sh] Fetching Kubernetes $resource..."
contexts=( "sandbox" "production" )

json='{'
for context in ${contexts[@]}
do
    kubectl config use-context $context
    json+="\"$context\": $(kubectl get $resource -o json),"
done
json=${json%,}
json+='}'

echo $json > "src/$resource.json"

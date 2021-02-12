#!/bin/bash
resource=$1
echo "Fetching Kubernetes $resource..."
contexts=( "sandbox" "production" )
jqargs=()
jqbody='{'
for context in ${contexts[@]}
do
    kubectl config use-context $context
    kubectl get $resource -o json > ../src/tmp-$context.json
    jqargs+=( "--slurpfile $context ../src/tmp-$context.json" )
    jqbody+="$context: \$$context, "
done
jqbody=${jqbody%, }
jqbody+='}'
echo $jqbody
jq -r ${jqargs[@]} '{sandbox: $sandbox, production: $production}' > ../src/$resource.json

cat ../src/ingress.json
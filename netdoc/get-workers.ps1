kubectl config use-context sandbox
$sandbox = kubectl get nodes --selector=node-role.kubernetes.io/worker -o json | ConvertFrom-Json
kubectl config use-context production
$production = kubectl get nodes --selector=node-role.kubernetes.io/worker -o json -o json | ConvertFrom-Json

$dict = @{}
$dict['sandbox'] = $sandbox
$dict['production'] = $production
$dict | ConvertTo-Json -depth 100 | Out-File Sources/workers.json

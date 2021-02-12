kubectl config use-context sandbox
$sandbox = kubectl get pods -o json | ConvertFrom-Json
kubectl config use-context production
$production = kubectl get pods -o json | ConvertFrom-Json

$dict = @{}
$dict['sandbox'] = $sandbox
$dict['production'] = $production
$dict | ConvertTo-Json -depth 100 | Out-File src/pods.json

kubectl config use-context sandbox
$sandbox = kubectl get ingress -o json | ConvertFrom-Json
kubectl config use-context production
$production = kubectl get ingress -o json | ConvertFrom-Json

$dict = @{}
$dict['sandbox'] = $sandbox
$dict['production'] = $production
$dict | ConvertTo-Json -depth 100 | Out-File Sources/ingress.json

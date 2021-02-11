Write-Host "Querying ActiveDirectory"
./get-ad.ps1
Write-Host "Building Docker image"
docker build -t netdox .
if ($? -eq 'True') {
    Write-Host "Build successful. Running container with name 'netdox-container'."
    docker run -it --name netdox-container netdox
}
else {
    Write-Host "Docker build failed."
}
function choosek8s {
    $choice = Read-Host "No Kubernetes config detected. Provide now? (y/n)"
    if ($choice.ToLower() -eq "y") {
        $kubepath = Read-Host "Enter the path of the .kube folder"
        if ((Test-Path -Path $kubepath) -eq 'True') {
            return $kubepath
        }
        else {
            Write-Host "Invalid path."
            choosek8s
        }
    }
    elseif ($choice.ToLower() -eq "n") {
        Write-Host "Proceeding without Kubernetes information..."
        return $null
    }
    else {
        Write-Host "Invalid input detected."
        choosek8s
    }
}

function chooseAD {
    $choice = Read-Host "ActiveDirectory query failed. Proceed anyway? (y/n)"
    if ($choice.ToLower() -eq 'y') {
        Write-Host "Proceeding..."
    }
    elseif ($choice.ToLower() -eq 'n') {
        exit
    }
    else {
        Write-Host "Invalid input detected."
        chooseAD
    }
}

function chooseAuth($name) {
    $choice = Read-Host "Missing or incomplete $name authentication details found in 'authentication.json'. Proceed anyway? (y/n)"
    if ($choice.ToLower() -eq 'y') {
        Write-Host "Proceeding..."
    }
    elseif ($choice.ToLower() -eq 'n') {
        exit
    }
    else {
        Write-Host "Invalid input detected."
        chooseAuth($name)
    }
}


$auth = Get-Content -Path "authentication.json" | ConvertFrom-Json

if (($auth.DNSMadeEasy.API -eq '') -or ($auth.DNSMadeEasy.Secret -eq '')) {
    chooseAuth('DNSMadeEasy')
}
if (($auth.XenOrchestra.Username -eq '') -or ($auth.XenOrchestra.Password -eq '')) {
    chooseAuth('Xen Orchestra')
}


$kubepath = Get-ChildItem $HOME ".kube" -Recurse -Exclude . -Directory -ErrorAction SilentlyContinue
# $kubepath = $kubepath.Replace('\','/')
# $kubepath -match '[A-Z]:/' | Out-Null
# $posixdrive = $Matches[0] | % {$_.Replace(':','')} | % {$_.ToLower()}
# $kubepath = $kubepath.Replace($Matches[0], "/mnt/$posixdrive")
# $kubepath = $kubepath.Replace(':','')
#Convert from windows path to posix path
if ($null -eq $kubepath) {
    $kubepath = choosek8s
    if ($null -ne $kubepath) {
        Write-Host "Kubernetes config detected."
        Copy-Item -Recurse -Force -Path $kubepath -Destination '.' | Out-Null
    }
    else {
        New-Item -ItemType "dicectory" -Name '.kube'
    }
}
else {
    Write-Host "Kubernetes config detected."
    Copy-Item -Recurse -Force -Path $kubepath -Destination '.' | Out-Null
}


Write-Host "Querying ActiveDirectory..."
./netdox/get-ad.ps1
if ($? -eq 'True') {
    Write-Host "ActiveDirectory query successful."
}
else {
    chooseAD
}

Set-Location -Path ".kube"
$KUBECONFIG = Get-ChildItem -Path "." -Filter "*config*" -File -Recurse | % {Resolve-Path -Relative -Path $_} | % {"/usr/.kube/${_}:" -replace '\\','/' -replace '/./','/'} | % {$_.TrimEnd(':')}
#Awful pipeline that adds all files in .kube to string and converts to absolute posix path in dir /usr/.kube/
Set-Location ".."
Write-Host "Building Docker image..."
docker build -t netdox --build-arg _kubeconfig=$KUBECONFIG .

if ($? -eq 'True') {
    Write-Host "Build successful. Starting container..."
    docker run -it netdox
}
else {
    Write-Host "Docker build failed."
}
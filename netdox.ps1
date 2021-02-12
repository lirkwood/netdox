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


$auth = Get-Content -Path "src/authentication.json" | ConvertFrom-Json

if (($auth.DNSMadeEasy.API -eq '') -or ($auth.DNSMadeEasy.Secret -eq '')) {
    chooseAuth('DNSMadeEasy')
}
if (($auth.XenOrchestra.Username -eq '') -or ($auth.XenOrchestra.Password -eq '')) {
    chooseAuth('Xen Orchestra')
}


$kubepath = Get-ChildItem $HOME ".kube" -Recurse -Directory -ErrorAction SilentlyContinue
if ($null -eq $kubepath) {
    $kubepath = choosek8s
    if ($null -ne $kubepath) {
        Write-Host "Kubernetes config detected."
    }
}
else {
    Write-Host "Kubernetes config detected."
}


Write-Host "Querying ActiveDirectory..."
./netdox/get-ad.ps1
if ($? -eq 'True') {
    Write-Host "ActiveDirectory query successful."
}
else {
    chooseAD
}


Write-Host "Building Docker image..."
if ($null -ne $kubepath) {
    docker build -t netdox --build-arg kubepath=$kubepath .
}
else {
    docker build -t netdox .
}

if ($? -eq 'True') {
    Write-Host "Build successful. Running container with name 'netdox-container'."
    docker run -it --name netdox-container netdox
}
else {
    Write-Host "Docker build failed."
}
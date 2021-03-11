function choosek8s {
    $choice = Read-Host "[WARNING][netdox.ps1] No Kubernetes config detected. Provide now? (y/n)"
    if ($choice.ToLower() -eq "y") {
        $kubepath = Read-Host "[INFO][netdox.ps1] Enter the path of the .kube folder"
        if ((Test-Path -Path $kubepath) -eq 'True') {
            return $kubepath
        }
        else {
            Write-Host "[ERRIR][netdox.ps1] Invalid path."
            choosek8s
        }
    }
    elseif ($choice.ToLower() -eq "n") {
        Write-Host "[INFO][netdox.ps1] Proceeding without Kubernetes information..."
        return $null
    }
    else {
        Write-Host "[ERROR][netdox.ps1] Invalid input detected."
        choosek8s
    }
}

function chooseAD {
    $choice = Read-Host "[WARNING][netdox.ps1] ActiveDirectory query failed. Proceed anyway? (y/n)"
    if ($choice.ToLower() -eq 'y') {
        Write-Host "[INFO][netdox.ps1] Proceeding..."
    }
    elseif ($choice.ToLower() -eq 'n') {
        exit
    }
    else {
        Write-Host "[ERROR][netdox.ps1] Invalid input detected."
        chooseAD
    }
}

function chooseAuth($name) {
    $choice = Read-Host "[WARNING][netdox.ps1] Missing or incomplete $name authentication details found in 'authentication.json'. Proceed anyway? (y/n)"
    if ($choice.ToLower() -eq 'y') {
        Write-Host "[INFO][netdox.ps1] Proceeding..."
    }
    elseif ($choice.ToLower() -eq 'n') {
        exit
    }
    else {
        Write-Host "[ERROR][netdox.ps1] Invalid input detected."
        chooseAuth($name)
    }
}

Start-Transcript -IncludeInvocationHeader -Path netdox-log.txt

$sw = [Diagnostics.Stopwatch]::StartNew()

$auth = Get-Content -Path "authentication.json" | ConvertFrom-Json

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
        Write-Host "[INFO][netdox.ps1] Kubernetes config detected."
        Copy-Item -Recurse -Force -Path $kubepath -Destination '.' | Out-Null
    }
    else {
        New-Item -ItemType "directory" -Name '.kube'
    }
}
else {
    Write-Host "[INFO][netdox.ps1] Kubernetes config detected."
    Copy-Item -Recurse -Force -Path $kubepath -Destination '.' | Out-Null
}


Write-Host "[INFO][netdox.ps1] Querying ActiveDirectory..."
./netdox/get-ad.ps1
if ($? -eq 'True') {
    Write-Host "[INFO][netdox.ps1] ActiveDirectory query successful."
}
else {
    chooseAD
}

Set-Location -Path ".kube"
$kubeconfig_array = Get-ChildItem -Path "." -Filter "*config*" -File -Recurse | % {Resolve-Path -Relative -Path $_} | % {"/usr/.kube/${_}:" -replace '\\','/' -replace '/./','/'}
$KUBECONFIG = -join $kubeconfig_array

# Awful pipeline that adds all files in .kube to string and converts to absolute posix path in dir /usr/.kube/
Set-Location ".."
Write-Host "[INFO][netdox.ps1] Building Docker image..."
docker build -t netdox --build-arg _kubeconfig=$KUBECONFIG .

if ($? -eq 'True') {
    docker container rm netdox | Out-Null
    Write-Host "[INFO][netdox.ps1] Build successful. Starting container..."
    docker run -it --name netdox netdox | Write-Host
}
else {
    Write-Host "[ERROR][netdox.ps1] Docker build failed."
}

$sw.Stop()
Write-Host $sw.Elapsed
Stop-Transcript
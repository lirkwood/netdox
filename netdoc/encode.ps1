foreach ($i in Get-ChildItem "Sources/records" -Recurse -Force) {
    if ($i.PSIsContainer) {
        continue
    }

    $path = $i.DirectoryName
    $name = $i.Fullname

    if ( !(Test-Path $path) ) {
        New-Item -Path $path -ItemType directory
    }

    $content = get-content $i.Fullname

    if (  $null -ne $content ) {

        [System.IO.File]::WriteAllLines($name, $content)
    } else {
        Write-Host "No content from: $i"   
    }
}

python json2xml.py
$Utf8NoBomEncoding = New-Object System.Text.UTF8Encoding($False)
$source = "../Sources/records"
$destination = "../Sources/records"

foreach ($i in Get-ChildItem -Recurse -Force) {
    if ($i.PSIsContainer) {
        continue
    }

    $path = $i.DirectoryName -replace $source, $destination
    $name = $i.Fullname -replace $source, $destination

    if ( !(Test-Path $path) ) {
        New-Item -Path $path -ItemType directory
    }

    $content = get-content $i.Fullname

    if (  $null -ne $content ) {

        [System.IO.File]::WriteAllLines($name, $content, $Utf8NoBomEncoding)
    } else {
        Write-Host "No content from: $i"   
    }
}

python json2xml.py

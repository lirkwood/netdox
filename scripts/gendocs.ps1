Push-Location
Set-Location "$PSScriptRoot\..\docs"
if (Test-Path ".\_source\source\") { Remove-Item .\_source\source\* }
if (Test-Path ".\_build\apidoc\*") { Remove-Item -Recurse .\_build\apidoc\* }
sphinx-apidoc --implicit-namespaces -M -T -o .\_source\source\ ..\src\netdox\
sphinx-build -Ea -b psml .\_source\ .\_build\apidoc
Pop-Location
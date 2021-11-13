Push-Location
Set-Location "$PSScriptRoot\docs"
Remove-Item .\_source\source\*
Remove-Item -Recurse .\_build\apidoc\*
sphinx-apidoc --implicit-namespaces -M -o .\_source\source\ ..\src\netdox\
sphinx-build -Ea .\_source\ .\_build\apidoc
Pop-Location
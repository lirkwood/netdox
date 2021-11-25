Push-Location
Set-Location "$PSScriptRoot\..\"
Remove-Item .\dist\*.whl
pip uninstall -y netdox
python setup.py bdist_wheel
Get-ChildItem .\dist\*.whl | % {pip install $_.FullName}
Pop-Location
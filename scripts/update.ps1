Remove-Item .\dist\*.whl
pip uninstall netdox
python setup.py bdist_wheel
Get-ChildItem .\dist\*.whl | % {pip install $_.Name}
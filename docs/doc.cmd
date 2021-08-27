pushd %~dp0
sphinx-apidoc --no-toc --implicit-namespaces -o _source/plugins ../netdox/plugins
del /q "_source\plugins\plugins.rst"
sphinx-build -aE _source _build/html
popd
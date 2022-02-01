#!/usr/bin/env bash

pushd .
cd $(dirname "$0")"/../docs"
[[ -d '_source/source' ]] && rm -f '_source/source/*'
[[ -d '_build/apidoc' ]] && rm -rf '_build/apidoc'
sphinx-apidoc --implicit-namespaces -M -T -o _source/source ../src/netdox
sphinx-build -Ea -b psml _source _build/apidoc
popd
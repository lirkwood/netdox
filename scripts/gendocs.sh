#!/usr/bin/env bash

pushd
cd dirname "$0/../docs"
rm -f _source/source/*
rm -rf _build/apidoc
sphinx-apidoc --implicit-namespaces -M -T -o _source/source ../src/netdox
sphinx-build -Ea -b psml _source _build/apidoc
popd
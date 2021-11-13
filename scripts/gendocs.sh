#!/usr/bin/env bash

pushd
cd dirname "$0/docs"
rm -f _source/source/*
rm -rf _build/apidoc
sphinx-apidoc --implicit-namespaces -M -o _source/source ../src/netdox
sphinx-build -Ea _source _build/apidoc
popd
#!/usr/bin/env bash

pip uninstall -y netdox
rm -f dist/*.whl
python3 setup.py bdist_wheel
for file in dist/*.whl; do pip install $file; done
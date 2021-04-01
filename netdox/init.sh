#!/bin/sh

cp -r /etc/ext/* /opt/app/src
ls -al /opt/app/src
python3 generate.py
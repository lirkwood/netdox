#!/bin/sh

cp -r /etc/ext/* /opt/app/src
ls -al /opt/app/src
chmod 777 /opt/app/*
python3 generate.py
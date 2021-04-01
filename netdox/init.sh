#!/bin/sh

mv /etc/ext/* /opt/app/src
ls -al /opt/app/src
chmod 777 /opt/app/*
python3 generate.py
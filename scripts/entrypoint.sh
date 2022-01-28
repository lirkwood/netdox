#!/usr/bin/env bash
netdox init /etc/netdox
netdox config dump /etc/netdox/config.json
netdox -d refresh
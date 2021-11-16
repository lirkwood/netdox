#!/usr/bin/env bash
netdox init /etc/netdox
netdox config load /etc/netdox/config.json
netdox config dump /etc/netdox/config.json
netdox refresh
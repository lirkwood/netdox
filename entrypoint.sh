#!/usr/bin/env bash

./netdox init
./netdox encrypt src/config.json src/config.bin
rm -f src/config.json
./netdox serve & ./netdox refresh
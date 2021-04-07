#!/bin/bash

echo '[INFO][init.sh] Pod started. Running init script...'

chmod 777 /opt/app/*

mkdir /opt/app/src/records
for file in /etc/nfs/*.bin; do
    filename=$(basename ${file%.bin})
    openssl enc -aes-256-cbc -d -in "$file" \
    -K ${OPENSSL_KEY} -iv $(cat '/etc/nfs/vector.txt') -out "/opt/app/src/records/${filename}.json" &> /dev/null
done

openssl enc -aes-256-cbc -d -in '/etc/ext/authentication.bin' \
-K ${OPENSSL_KEY} -iv $(printf authivpassphrase | xxd -p) -out '/opt/app/src/authentication.json'

python3 generate.py
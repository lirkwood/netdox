#!/bin/bash

echo '[INFO][init.sh] Pod started. Running init script...'

chmod 777 /opt/app/*

mkdir /opt/app/src/records
for file in /etc/nfs/*.bin; do
    openssl enc -aes-256-cbc -d -in "$file" \
    -K ${OPENSSL_KEY} -iv $(cat '/etc/nfs/vector.txt') -out "/opt/app/src/records/$(basename ${file%.bin}).json" &> /dev/null
done

for file in /etc/ext/*.bin; do
    openssl enc -aes-256-cbc -d -in "$file" \
    -K ${OPENSSL_KEY} -iv $(printf authivpassphrase | xxd -p) -out "/opt/app/src/$(basename $file)"
done

python3 generate.py
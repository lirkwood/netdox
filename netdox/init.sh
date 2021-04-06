#!/bin/sh

cp -r /etc/ext/* /opt/app/src
chmod 777 /opt/app/*

for file in "/opt/app/src/records/*.bin"; do
    openssl enc -aes-256-cbc -d -in "$file" \
    -K ${OPENSSL_KEY} -iv $(cat '/opt/app/src/records/vector.txt') -out "${file%.bin}"
done

python3 generate.py
#!/bin/bash

echo '[INFO][init.sh] Pod started. Running init script...'

chmod 777 /opt/app/*

mkdir /opt/app/src/records
for file in /etc/nfs/*.bin; do
    openssl enc -aes-256-cbc -d -in "$file" \
    -K ${OPENSSL_KEY} -iv $(cat '/etc/nfs/vector.txt') -out "/opt/app/src/records/$(basename ${file%.bin}).json" &> /dev/null
done

openssl enc -aes-256-cbc -d -in "/etc/ext/authentication.bin" \
-K ${OPENSSL_KEY} -iv $(printf authivpassphrase | xxd -p) -out "/opt/app/src/authentication.json"

if python3 init.py
    then
        echo '[INFO][init.sh] Python initialisation successful.'
    else
        echo '[ERROR][init.sh] Python initialisation unsuccessful. Terminating...'
        exit 1
fi

crontab <<< '0 8 * * * ./refresh.sh'

echo '[IMNFO][init.sh] Starting gunicorn server on 8080'

gunicorn --reload -b '0.0.0.0:8080' serve:app
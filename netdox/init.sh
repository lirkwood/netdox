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


if python3 netdox.py
    then
        echo '[INFO][init.sh] Python exited successfully. Beginning PageSeeder upload...'
        cd /opt/app/out
        zip -r -q netdox-src.zip *
        cd /opt/app
        if ant -lib /opt/ant/lib
            then
                echo '[INFO][init.sh] Upload successful.'
            else
                echo '[ERROR][init.sh] Upload exited with non-zero status. Storing psml for debugging...'
                cp /opt/app/out/netdox-src.zip /etc/ext/psml.zip
        fi
    else
        echo '[ERROR][init.sh] Python exited with non-zero status. Cancelling upload...'
fi

echo '[INFO][init.sh] Done.'

#!/bin/bash

echo '[INFO][init.sh] Pod started. Running init script...'

chmod 777 /opt/app/*

mkdir /opt/app/src/records
for file in /etc/nfs/*.bin; do
    ./crypto.sh decrypt '/etc/nfs/vector.txt' "$file" "/opt/app/src/records/$(basename ${file%.bin}).json" &> /dev/null
done

./crypto.sh decrypt $(printf authivpassphrase | xxd -p) "/etc/ext/authentication.bin" "/opt/app/src/authentication.json"

mkdir /root/.ssh
cp /etc/ssh-inf/ssh-publickey /root/.ssh/id_rsa.pub
cp /etc/ssh-inf/ssh-privatekey /root/.ssh/id_rsa
chmod 600 /root/.ssh/*

if python3 init.py
    then
        echo '[INFO][init.sh] Python initialisation successful.'
    else
        echo '[ERROR][init.sh] Python initialisation unsuccessful. Terminating...'
        exit 1
fi

crontab <<< '0 8 * * * ./refresh.sh | tee /var/log/refresh-$(date +%F-T%T).log'

echo -e '[INFO][init.sh] Starting gunicorn server on 8080\n'

gunicorn --reload -b '0.0.0.0:8080' serve:app
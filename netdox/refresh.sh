#!/bin/bash

if python3 refresh.py
    then
        echo '[INFO][refresh.sh] Python exited successfully. Beginning PageSeeder upload...'
        cd /opt/app/out
        zip -r -q netdox-src.zip *
        cd /opt/app
        if ant -lib /opt/ant/lib
            then
                echo '[INFO][refresh.sh] Upload successful.'
            else
                echo '[ERROR][refresh.sh] Upload exited with non-zero status. Storing psml for debugging...'
                cp /opt/app/out/netdox-src.zip /etc/ext/psml.zip
        fi
    else
        echo '[ERROR][refresh.sh] Python exited with non-zero status. Cancelling upload...'
fi
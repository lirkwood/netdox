#!/usr/bin/env bash

APPDIR=$(dirname $(realpath $0))

## Print usage help
function help {
    echo 'Methods'
    echo 'init:                           Initialises the environment and generates a new cryptographic key.'
    echo 'serve:                          Starts a Gunicorn web server listening for webhooks from the configured PageSeeder.'
    echo 'refresh:                        Generates a new set of PSML documents and uploads them to PageSeeder,'
    echo 'encrypt <infile> [outfile]:     Encrypts a file using the internal cryptography from infile to outfile.'
    echo 'decrypt <infile> [outfile]:     Decrypts a file using the internal cryptography from infile to outfile.'
}

## Initialise container with provided config to allow other processes to run
function init {
    if [[ ! -f $APPDIR/src/config.bin ]]
        then
            echo '[WARNING][netdox] Primary configuration file missing. Please place config.bin in src/'
            exit 1 
    fi

    # make all scripts executable
    chmod 744 *

    if python3 -m netdox.init
        then
            echo '[INFO][netdox] Initialisation successful.'
            chmod 500 $APPDIR/src/crypto
        else
            echo '[ERROR][netdox] Initialisation unsuccessful. Please try again.'
            exit 1
    fi
}

## Refresh dataset and upload to PageSeeder
function refresh {
    python3 -m netdox.refresh
}

## Serve webhook listener
function serve {
    gunicorn --reload -b '0.0.0.0:8080' -t 900 serve:app
}

## Encrypt a file to a Fernet token
function encrypt {
    python3 -m netdox.crypto 'encrypt' $1 $2
}

## Decrypt a file from a Fernet token
function decrypt {
    python3 -m netdox.crypto 'decrypt' $1 $2
}


method=$1
declare -a args
for arg in $@; do
    if [[ "$arg" != "$method" ]]
        then args+=("$arg")
    fi
done

methods=("init" "serve" "refresh" "encrypt" "decrypt")
if [[ ${methods[@]} =~ "$method" ]]
    then $method ${args[@]}; else help
fi
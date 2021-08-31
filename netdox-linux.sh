#!/usr/bin/env bash

APPDIR=$(dirname $(realpath $0))

## Print usage help
function help {
    echo 'Methods'
    echo 'init:                           Initialises the environment and generates a new cryptographic key.'
    echo 'config:                         Encrypts the file and moves it to the config location (src/config.bin). Will also test the connection to PageSeeder.'
    echo 'serve:                          Starts a Gunicorn web server listening for webhooks from the configured PageSeeder.'
    echo 'refresh:                        Generates a new set of PSML documents and uploads them to PageSeeder,'
    echo 'encrypt <infile> [outfile]:     Encrypts a file using the internal cryptography from infile to outfile.'
    echo 'decrypt <infile> [outfile]:     Decrypts a file using the internal cryptography from infile to outfile.'
}

## Initialise container with provided config to allow other processes to run
function init {
    if [[ -f $APPDIR/src/config.bin ]]
        then
            echo '[WARNING][netdox] This will generate a new cryptographic key, and your current configuration will be lost. Remove the config file to confirm this action.'
            exit 1
    fi

    # make all scripts executable
    chmod 744 *

    if python3 -m netdox.init
        then
            echo '[INFO][netdox] Initialisation successful. Please run load a config file.'
            chmod 500 $APPDIR/netdox/src/crypto
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

## Load a file as config.bin
function config {
    if [[ -f "$APPDIR/netdox/src/config.bin" ]]; then
        encrypt $1 "$APPDIR/netdox/src/config.bin"
        if python3 -m netdox.PageSeeder
            then
                rm -f $1
                echo '[INFO][netdox] Success: configuration is valid.'
            else
                echo '[ERROR][netdox] Unable to contact or authenticate with the configured PageSeeder instance. Please check your configuration and try again.'
                exit 1
        fi
    else
        echo "[ERROR][netdox] Unable to find or parse config file at: $1"
    fi
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

methods=("init" "config" "serve" "refresh" "encrypt" "decrypt")
if [[ ${methods[@]} =~ "$method" ]]
    then $method ${args[@]}; else help
fi
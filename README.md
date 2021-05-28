# Netdox

Full documentation is available [here](https://netdox.allette.com.au/documentation.hmtl).

## Using this project

A persistent volume must be mounted at `/etc/ext`. The only required file is `cfg/authentication.json` (template is available in the root of this project) with valid credentials for a working and available PageSeeder instance.

Once the container is running use `netdox start` to initialise Netdox and begin refreshing the DNS data.
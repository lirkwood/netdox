# Netdox

Full documentation is available [here](https://netdox.allette.com.au/documentation.hmtl).

## Using this project

Simply start a docker container / kubernetes pod running one of the images from the container registry, or clone the project and build the image yourself using `docker build`.

A persistent volume must be mounted at `/etc/ext`. The only required file is `config.json` (template is available in the root of this project) with valid credentials for a working and available PageSeeder instance. It must be placed in the `cfg/` sub-path of the persistent volume. It should be encrypted using AES-256-CBC and the secret key should be available under the `OPENSSL_KEY` environment variable within the container.

Once the container is running the initialisation will begin and the webserver will start listening for webhooks. Use `netdox refresh` to refresh the DNS data or `netdox help` for more commands.
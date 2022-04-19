## Public Readme Addendum
This is a public repo for netdox occasionally updated from the Allette gitlab. The internal documentation link below wont work, so I have added a copy of the documentation in HTML at `./docs/html/`.

If you haven't already, familiarise yourself with [PageSeeder](https://pageseeder.com/), which this app is designed to work directly with.

---
# Netdox
Full documentation is available [here](https://netdox.allette.com.au/index.html).

`netdox init` will initialise a directory as the designated config directory. This location will be used to hold any configuration files that do not require encryption. Templates for all config files with also be copied here.

Once you have chosen your config directory, use `netdox config load` to load and encrypt the primary config file (template for this file is named `config.json`).
You may need to read the README files for the plugins you wish to use while populating this file.

If this is successful, you are ready to begin using netdox. Try `netdox refresh`!
For more help run `netdox -h` and `netdox <method> -h`.

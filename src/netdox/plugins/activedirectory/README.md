### DNS Plugin
---
# ActiveDirectory

## Configuring this plugin

In order for this plugin to run, a directory of encrypted JSON files should be present at `activedirectory/nfs/`. 
Each file should be in the format given by the Powershell command `Get-DnsServerResourceRecord | ConvertTo-Json -Depth 10`.
Also in this directory should be a text file named ``vector.txt`` containing the initialisation vector used to encrypt the files.
During initialisation the plugin will attempt to decrypt any files that match `activedirectory/nfs/*.bin` extension using the `crypto.sh` script with the content of `vector.txt` as the IV.

## Creating DNS records

When triggered by a webhook, this plugin will write JSON to the file `activedirectory/nfs/scheduled.bin`. It will not take any other action, and expects that however the data in `activedirectory/nfs/` is updated, the records specified in `scheduled.bin` will be created at the same time.
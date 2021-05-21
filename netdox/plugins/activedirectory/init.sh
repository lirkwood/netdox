mkdir plugins/activedirectory/records
# decrypt files
for file in plugins/activedirectory/nfs/*.bin; do
    ./crypto.sh decrypt 'plugins/activedirectory/nfs/vector.txt' "$file" "plugins/activedirectory/records/$(basename ${file%.bin}).json" &>/dev/null
done
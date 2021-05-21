mkdir plugins/activedirectory/src/records
# decrypt files
for file in plugins/activedirectory/nfs/*.bin; do
    ./crypto.sh decrypt 'plugins/activedirectory/vector.txt' "$file" "plugins/activedirectory/src/records/$(basename ${file%.bin}).json" &> /dev/null
done
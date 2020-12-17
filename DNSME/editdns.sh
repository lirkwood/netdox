base='https://api.dnsmadeeasy.com/V2.0/dns/managed/' #base url
domain=$1
name=$2
type=$3
value=$4

while getopts ":d:n:t:v:" arg; do
    case "${arg}" in 
        d)
            domain=${OPTARG}
            ;;
        n)
            name=${OPTARG}
            ;;
        t)
            type=${OPTARG}
            ;;
        v)
            value=${OPTARG}7
            ;;
    esac
done

domainid=$(python3 -c "import json; f=open('domainids.json','r'); d=json.load(f); print(d['${domain}']); f.close()")

IFS=' '
keys=$(cat dnsme.txt)

first=1
for key in ${keys}
do
    if [ $first == 1 ]
        then
            first=0
            apiKey=${key}
        else
            secretKey=${key}
    fi
done

unset IFS

date=$(date -R)
signature=$(echo -en ${date} | openssl sha1 -hmac ${secretKey} -binary | xxd -p )

# recordid=$(curl -s -X GET "${base}${domainid}/records?recordName=${name}&type=${type}" \
# --header 'Content-Type: application/json' \
# --header "x-dnsme-hmac: ${signature}" \
# --header "x-dnsme-apiKey: ${apiKey}" \
# --header "x-dnsme-requestDate: ${date}" | \
# python3 -c "import sys, json; print(json.load(sys.stdin)['data'][0]['id'])" )

# body='{"name":"'"${name}"'","type":"'"${type}"'","value":"'"${value}"'","id":"'"${recordid}"'","gtdLocation":"DEFAULT","ttl":120}'

# curl -s -X PUT "https://api.dnsmadeeasy.com/V2.0/dns/managed/${domainid}/records/${recordid}" \
# --header 'Content-Type: application/json' \
# --header "x-dnsme-hmac: ${signature}" \
# --header "x-dnsme-apiKey: ${apiKey}" \
# --header "x-dnsme-requestDate: ${date}" \
# --data-raw "${body}"

echo $recordid
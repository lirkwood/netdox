import requests, json

headers = {
    "Accept": "application/json",
}

r = requests.get('https://icinga.allette.com.au:5665/v1/objects/hosts', auth=('root','8a2b3a827f09c18c'), verify=False)

response = json.loads(r.text)
with open('icinga_log.json','w') as stream:
    stream.write(json.dumps(response, indent=2))

def lookup(list):
    for _obj in response['results']:
        obj = _obj['attrs']
        if obj['address'] in list:
            return obj
    return None
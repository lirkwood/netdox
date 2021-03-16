import requests, json

headers = {
    "Accept": "application/json",
}

with open('src/authentication.json','r') as stream:
    credentials = json.load(stream)['icinga']

objects = []
for host in ('icinga.allette.com.au', 'icinga-sy4.allette.com.au'):
    r = requests.get(f'https://{host}:5665/v1/objects/hosts', auth=(credentials["username"], credentials["password"]), verify=False)
    response = json.loads(r.text)
    try:
        for obj in response["results"]:
            objects.append(obj)
    except KeyError:
        print(f'[ERROR][icinga_inf.py] Icinga query on host {host} failed. Proceeding anyway...')
    

with open('src/icinga_log.json','w') as stream:
    stream.write(json.dumps(response, indent=2))

def lookup(list):
    for _obj in objects:
        obj = _obj['attrs']
        if obj['address'] in list:
            return obj
    return None
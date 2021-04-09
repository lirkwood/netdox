import requests, utils, json

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

@utils.handle
def lookup(list):
    for _obj in objects:
        obj = _obj['attrs']
        # if any host object in icinga has value present in <list> return obj
        if obj['address'] in list:
            return obj
        # if any host object has http service on a value presetn in <list> return obj
        elif ('vars' in obj) and ('http_vhosts' in obj['vars']):
            for _vhost in obj['vars']['http_vhosts']:
                vhost = obj['vars']['http_vhosts'][_vhost]
                if ("http_address" in vhost) and (vhost["http_address"] in list):
                    return obj
    return None
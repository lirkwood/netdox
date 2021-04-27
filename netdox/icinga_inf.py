import requests, json

with open('src/authentication.json','r') as stream:
    hosts = json.load(stream)['icinga']

def fetchObjects():
    objects = {}
    for host in hosts:
        creds = hosts[host]
        r = requests.get(f'https://{host}:5665/v1/objects/hosts', auth=(creds["username"], creds["password"]), verify=False)
        response = json.loads(r.text)
        try:
            for obj in response["results"]:
                name = obj['attrs']['__name']
                addr = obj['attrs']
                objects[addr] = name
                for vhost in obj['attrs']['vars']['http_vhosts'].keys():
                    objects[vhost] = name
        except KeyError:
            print(f'[WARNING][icinga_inf.py] Icinga query on host {host} failed. Proceeding anyway...')
    return objects
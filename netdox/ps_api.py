import requests, utils, json
from bs4 import BeautifulSoup
from datetime import datetime

# Auth info

with open('src/authentication.json','r') as stream:
    credentials = json.load(stream)['pageseeder']

defaultgroup = credentials['group']


# Useful services

@utils.critical
def auth():
    try:
        print('[INFO][ps_api.py] Requesting new access token...')
        url = f'https://{credentials["host"]}/ps/oauth/token'
        refresh_header = {
            'grant_type': 'client_credentials',
            'client_id': credentials['id'],
            'client_secret': credentials['secret']
        }

        r = requests.post(url, params=refresh_header)
        token = json.loads(r.text)['access_token']

        return token

    except KeyError:
        print('[ERROR][ps_api.py] PageSeeder authentication failed.')
        quit()


@utils.silent
def get_uri(uri, group=defaultgroup):
    service = f'/groups/~{group}/uris/{uri}'
    r = requests.get(base+service, headers=header)
    return r.text

@utils.silent
def get_uris(uri, group=defaultgroup, params={}):
    if 'pagesize' not in params:
        params['pagesize'] = 9999

    service = f'/groups/~{group}/uris/{uri}/uris'
    r = requests.get(base+service, headers=header, params=params)
    return r.text


@utils.silent
def get_files(uri, group=defaultgroup): # returns list of filenames in a folder on pageseeder
    files = []
    soup = BeautifulSoup(get_uris(uri, group, {'type': 'document'}), features='xml')
    for uri in soup.find_all('uri'):
        files.append(uri['path'].split('/')[-1])
    
    return files

@utils.silent
def get_fragment(uri, fragment_id, params={}):
    service = f'/members/~{credentials["username"]}/groups/~{defaultgroup}/uris/{uri}/fragments/{fragment_id}'
    r = requests.get(base+service, headers=header, params=params)
    return r.text


@utils.silent
def export(uri, params={}):
    service = f'/members/~{credentials["username"]}/uris/{uri}/export'
    r = requests.get(base+service, headers=header, params=params)
    return r.text


@utils.silent
def get_thread(id):
    service = f'/threads/{id}/progress'
    r = requests.get(base+service, headers=header)
    return r.text



@utils.silent
def archive(uri):
    service = f'/members/~{credentials["username"]}/groups/~{defaultgroup}/uris/{uri}/archive'
    r = requests.post(base+service, headers=header)
    return r


@utils.silent
def version(uri):
    service = f'/members/~{credentials["username"]}/groups/~{defaultgroup}/uris/{uri}/versions'
    requests.post(base+service, headers=header, params={'name': datetime.now().replace(microsecond=0)})   # version all docs that are not archived => current



# Global vars

header = {
    'authorization': f'Bearer {auth()}'
}

base = f'https://{credentials["host"]}/ps/service'

if __name__ == '__main__':
    print(header['authorization'])
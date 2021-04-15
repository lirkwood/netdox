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
    """
    Returns authentication token for PageSeeder API
    """
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
def get_uri(locator, params={}, forurl=False, group=defaultgroup):
    """
    Returns some info on a uri
    """
    if forurl:
        service = f'/groups/~{group}/uris/forurl'
        params["url"] = locator
    else:
        service = f'/groups/~{group}/uris/{locator}'

    r = requests.get(base+service, headers=header, params=params)
    return r.text

@utils.silent
def get_uris(uri, group=defaultgroup, params={}):
    """
    Returns all uris with some relationship to a given uri
    """
    if 'pagesize' not in params:
        params['pagesize'] = 9999

    service = f'/groups/~{group}/uris/{uri}/uris'
    r = requests.get(base+service, headers=header, params=params)
    return r.text


@utils.silent
def get_files(uri, group=defaultgroup):
    """
    Returns a list of filenames with some relationship (default = child) for a given URI
    """
    files = []
    soup = BeautifulSoup(get_uris(uri, group, {'type': 'document'}), features='xml')
    for uri in soup.find_all('uri'):
        files.append(uri['path'].split('/')[-1])
    
    return files

@utils.silent
def get_fragment(uri, fragment_id, params={}):
    """
    Returns content of a fragment in some given uri
    """
    service = f'/members/~{credentials["username"]}/groups/~{defaultgroup}/uris/{uri}/fragments/{fragment_id}'
    r = requests.get(base+service, headers=header, params=params)
    return r.text


@utils.silent
def export(uri, params={}):
    """
    Begins export process for some URI and returns relevant thread ID
    """
    service = f'/members/~{credentials["username"]}/uris/{uri}/export'
    r = requests.get(base+service, headers=header, params=params)
    return r.text


@utils.silent
def get_thread(id):
    """
    Returns information about some PageSeeder process thread
    """
    service = f'/threads/{id}/progress'
    r = requests.get(base+service, headers=header)
    return r.text


@utils.silent
def archive(uri):
    """
    Begins archive process for some URI
    """
    service = f'/members/~{credentials["username"]}/groups/~{defaultgroup}/uris/{uri}/archive'
    r = requests.post(base+service, headers=header)
    return r


@utils.silent
def version(uri):
    """
    Adds a version to some URI with name as current date/time
    """
    service = f'/members/~{credentials["username"]}/groups/~{defaultgroup}/uris/{uri}/versions'
    requests.post(base+service, headers=header, params={'name': datetime.now().replace(microsecond=0)})   # version all docs that are not archived => current



# Global vars

header = {
    'authorization': f'Bearer {auth()}'
}

base = f'https://{credentials["host"]}/ps/service'

if __name__ == '__main__':
    print(header['authorization'])
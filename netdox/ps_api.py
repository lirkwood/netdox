import requests, utils, json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# Setting global vars

credentials = utils.auth['pageseeder']

defaultgroup = credentials['group']
base = f'https://{credentials["host"]}/ps/service'
member = credentials['username']


# Useful services

def auth():
    """
    Returns authentication token for PageSeeder API
    """
    try:
        with open('src/pstoken.json', 'r') as stream:
            details = json.load(stream)
            token = details['token']
            issued = details['issued']

            if datetime.fromisoformat(issued) > (datetime.now() - timedelta(hours=1)):
                return token
            else:
                return refreshToken()
    except FileNotFoundError:
        refreshToken()

def refreshToken():
    with open('src/pstoken.json', 'w') as stream:
        print('[INFO][ps_api.py] Requesting new access token...')

        url = f'https://{credentials["host"]}/ps/oauth/token'
        refresh_header = {
            'grant_type': 'client_credentials',
            'client_id': credentials['id'],
            'client_secret': credentials['secret']
        }

        r = requests.post(url, params=refresh_header)
        token = json.loads(r.text)['access_token']
        issued = datetime.isoformat(datetime.now())
        stream.write(json.dumps({
            'token': token,
            'issued': str(issued)
        }, indent=2))

    return token


@utils.handle
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

@utils.handle
def get_uris(uri, params={}, group=defaultgroup):
    """
    Returns all uris with some relationship to a given uri
    """
    if 'pagesize' not in params:
        params['pagesize'] = 9999

    service = f'/groups/~{group}/uris/{uri}/uris'
    r = requests.get(base+service, headers=header, params=params)
    return r.text


@utils.handle
def get_files(uri, params={}, group=defaultgroup):
    """
    Returns a list of filenames with some relationship (default = child) for a given URI
    """
    files = []
    if 'type' not in params:
        params['type'] = 'document'
    soup = BeautifulSoup(get_uris(uri, params, group), features='xml')
    for uri in soup.find_all('uri'):
        files.append(uri['path'].split('/')[-1])
    
    return files

@utils.handle
def get_fragment(uri, fragment_id, params={}, group=defaultgroup):
    """
    Returns content of a fragment in some given uri
    """
    service = f'/members/~{member}/groups/~{group}/uris/{uri}/fragments/{fragment_id}'
    r = requests.get(base+service, headers=header, params=params)
    return r.text


@utils.handle
def export(uri, params={}):
    """
    Begins export process for some URI and returns relevant thread ID
    """
    service = f'/members/~{member}/uris/{uri}/export'
    r = requests.get(base+service, headers=header, params=params)
    return r.text


@utils.handle
def get_thread(id):
    """
    Returns information about some PageSeeder process thread
    """
    service = f'/threads/{id}/progress'
    r = requests.get(base+service, headers=header)
    return r.text


@utils.handle
def archive(uri, params={}, group=defaultgroup):
    """
    Begins archive process for some URI
    """
    service = f'/members/~{member}/groups/~{group}/uris/{uri}/archive'
    r = requests.post(base+service, headers=header, params=params)
    return r.text


@utils.handle
def version(uri, params={}, group=defaultgroup):
    """
    Adds a version to some URI. Default name is current date/time
    """
    if 'name' not in params:
        params['name'] = datetime.now().replace(microsecond=0)
        
    service = f'/members/~{member}/groups/~{group}/uris/{uri}/versions'
    r = requests.post(base+service, headers=header, params=params)   # version all docs that are not archived => current
    return r.text


@utils.handle
def get_versions(uri, group=defaultgroup):
    """
    Lists the versions 
    """
    service = f'/groups/{group}/uris/{uri}/versions'
    r = requests.get(base+service, headers=header)
    return r.text


@utils.handle
def patch_uri(uri, params={}, group=defaultgroup):
    """
    Sets the specified properties of a URI
    """
    service = f'/members/{member}/groups/{group}/uris/{uri}'
    r = requests.patch(base+service, headers=header, params=params)
    return r.text

@utils.handle
def get_groupfolder(id, params={}, group=defaultgroup):
    """
    Gets some groupfolder
    """
    service = f'/members/{member}/groups/{group}/groupfolders/{id}'
    r = requests.get(base+service, headers=header, params=params)
    return r.text

@utils.handle
def get_groupfolders(params={}, group=defaultgroup):
    """
    Gets the groupfolders for some group
    """
    service = f'/members/{member}/groups/{group}/groupfolders'
    r = requests.get(base+service, headers=header, params=params)
    return r.text


@utils.handle
def get_comment(commentid, params={}):
    """
    Gets some comment
    """
    service = f'/members/{credentials["username"]}/comments/{commentid}'
    r = requests.get(base+service, headers=header, params=params)
    return r.text


@utils.handle
def get_xrefs(uri, params={}, group=defaultgroup):
    """
    Gets the xrefs of some uri
    """
    service = f'/groups/{group}/uris/{uri}/xrefs'
    r = requests.get(base+service, headers=header, params=params)
    return r.text


@utils.handle
def getUrimap(dir_uri):
    """
    Maps the directories in a URI to their URIs
    """
    urimap = {}
    uris = json.loads(get_uris(dir_uri, params={'type': 'folder'}))
    for uri in uris['uris']:
        urimap[uri['displaytitle']] = uri['id']
    return urimap


def pfrag2dict(fragment):
    if isinstance(fragment, str):
        fragment = BeautifulSoup(fragment, features='xml')
    elif not isinstance(fragment, BeautifulSoup):
        raise TypeError(f'[ERROR][ps_api.py] Fragment but be one of: str, BeautifulSoup. Not {type(fragment)}')
    
    d = {}
    for property in fragment("property"):
        if property.xref:
            d[property['name']] = property.xref.string
        else:
            d[property['name']] = property['value']
    
    return d

# some global vars

header = {
    'authorization': f'Bearer {auth()}',
    'Accept': 'application/json'
}

urimap = getUrimap('375156')

if __name__ == '__main__':
    print(auth())
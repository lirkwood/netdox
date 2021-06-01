"""
Used to interface with the PageSeeder REST API for numerous operations throughout Netdox's lifecycle.

Provides many various convenience functions for PageSeeder API actions, returning JSON where possible.
The decorator ``@auth`` injects default values and authentication details to the most of the functions in this script.
"""

import requests, utils, json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from functools import wraps
from inspect import signature


#####################
# Utility functions #
#####################

def refreshToken(credentials: dict) -> str:
    """
    Requests a new PageSeeder API authentication token and saves it to disk.

    :Args:
        A dictionary containing some authentication/configuration details. Found in ``authentication.json``.

    :Returns:
        A string containing a valid PageSeeder API token.
    """
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

def auth(func):
    """
    Authenticates a PageSeeder API request function.

    Reads existing PageSeeder authentication token, refreshes it if expired,
    and replaces the passed function's kwarg *header* with its own value.
    Also passes some other global kwargs (e.g. group) if not otherwise specified.
    Also applies the ``@utils.handle`` functionality (see :ref:`utils`).
    
    :Args:
        Some function to be authenticated which makes a PageSeeder REST API request and takes the kwarg *header*.
    """
    
    credentials = utils.auth()['pageseeder']
    try:
        with open('src/pstoken.json', 'r') as stream:
            details = json.load(stream)
            token = details['token']
            issued = details['issued']

            if datetime.fromisoformat(issued) <= (datetime.now() - timedelta(hours=1)):
                token = refreshToken(credentials)
    except FileNotFoundError:
        token = refreshToken(credentials)
    
    defaults = {
        'host': f'https://{credentials["host"]}/ps/service',
        'member': credentials['username'],
        'group': credentials['group'],
        'header': {
                'authorization': f'Bearer {token}',
                'Accept': 'application/json'
            }
    }

    @wraps(func)
    def wrapper(*args, **kwargs):
        for kw in signature(func).parameters:
            if kw not in kwargs and kw in defaults:
                kwargs[kw] = defaults[kw]
        return utils.handle(func)(*args, **kwargs)

    return wrapper

# global urimap
global _urimap
def urimap():
    """
    Returns value of default urimap if it has already been fetched. If not, it is fetched and returned.

    :Returns:
        Same as ``getUrimap()``
    """
    try:
        return _urimap
    except NameError:
        _urimap = getUrimap('375156')
        return _urimap


##########################
# PageSeeder API Actions #
##########################

@auth
def get_uri(locator, params={}, forurl=False, host='', group='', header={}):
    """
    Returns some info on a uri
    """
    if forurl:
        service = f'/groups/~{group}/uris/forurl'
        params["url"] = locator
    else:
        service = f'/groups/~{group}/uris/{locator}'

    r = requests.get(host+service, headers=header, params=params)
    return r.text

@auth
def get_uris(uri, params={}, host='', group='', header={}):
    """
    Returns all uris with some relationship to a given uri
    """
    if 'pagesize' not in params:
        params['pagesize'] = 9999

    service = f'/groups/~{group}/uris/{uri}/uris'
    r = requests.get(host+service, headers=header, params=params)
    return r.text


@auth
def get_files(uri, params={}, group=''):
    """
    Returns a list of filenames with some relationship (default = child) for a given URI
    """
    files = []
    if 'type' not in params:
        params['type'] = 'document'
    soup = BeautifulSoup(get_uris(uri, params, group=group), features='xml')
    for uri in soup.find_all('uri'):
        files.append(uri['path'].split('/')[-1])
    
    return files

@auth
def get_fragment(uri, fragment_id, params={}, host='', group='', member='', header={}):
    """
    Returns content of a fragment in some given uri
    """
    service = f'/members/~{member}/groups/~{group}/uris/{uri}/fragments/{fragment_id}'
    r = requests.get(host+service, headers=header, params=params)
    return r.text


@auth
def export(uri, params={}, host='', member='', header={}):
    """
    Begins export process for some URI and returns relevant thread ID
    """
    service = f'/members/~{member}/uris/{uri}/export'
    r = requests.get(host+service, headers=header, params=params)
    return r.text


@auth
def get_thread(id, host='', header={}):
    """
    Returns information about some PageSeeder process thread
    """
    service = f'/threads/{id}/progress'
    r = requests.get(host+service, headers=header)
    return r.text


@auth
def archive(uri, params={}, host='', group='', member='', header={}):
    """
    Begins archive process for some URI
    """
    service = f'/members/~{member}/groups/~{group}/uris/{uri}/archive'
    r = requests.post(host+service, headers=header, params=params)
    return r.text


@auth
def version(uri, params={}, host='', group='', member='', header={}):
    """
    Adds a version to some URI. Default name is current date/time
    """
    if 'name' not in params:
        params['name'] = datetime.now().replace(microsecond=0)
        
    service = f'/members/~{member}/groups/~{group}/uris/{uri}/versions'
    r = requests.post(host+service, headers=header, params=params)   # version all docs that are not archived => current
    return r.text


@auth
def get_versions(uri, host='', group='', header={}):
    """
    Lists the versions 
    """
    service = f'/groups/{group}/uris/{uri}/versions'
    r = requests.get(host+service, headers=header)
    return r.text


@auth
def patch_uri(uri, params={}, host='', group='', member='', header={}):
    """
    Sets the specified properties of a URI
    """
    service = f'/members/{member}/groups/{group}/uris/{uri}'
    r = requests.patch(host+service, headers=header, params=params)
    return r.text

@auth
def get_groupfolder(id, params={}, host='', group='', member='', header={}):
    """
    Gets some groupfolder
    """
    service = f'/members/{member}/groups/{group}/groupfolders/{id}'
    r = requests.get(host+service, headers=header, params=params)
    return r.text

@auth
def get_groupfolders(params={}, host='', group='', member='', header={}):
    """
    Gets the groupfolders for some group
    """
    service = f'/members/{member}/groups/{group}/groupfolders'
    r = requests.get(host+service, headers=header, params=params)
    return r.text


@auth
def get_comment(commentid, params={}, host='', member='', header={}):
    """
    Gets some comment
    """
    service = f'/members/{member}/comments/{commentid}'
    r = requests.get(host+service, headers=header, params=params)
    return r.text


@auth
def get_xrefs(uri, params={}, host='', group='', header={}):
    """
    Gets the xrefs of some uri
    """
    service = f'/groups/{group}/uris/{uri}/xrefs'
    r = requests.get(host+service, headers=header, params=params)
    return r.text


@auth
def get_xref_tree(uri, params={}, host='', group='', header={}):
    """
    Gets the xref tree for some uri
    """
    service = f'/groups/{group}/uris/{uri}/xreftree'
    r = requests.get(host+service, headers=header, params=params)
    return r.text


@auth
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
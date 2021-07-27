"""
Used to interface with the PageSeeder REST API for numerous operations throughout Netdox's lifecycle.

Provides many various convenience functions for PageSeeder API actions, returning JSON where possible.
The decorator ``@auth`` injects default values and authentication details to the most of the functions in this script.
"""

import json
from datetime import datetime, timedelta
from functools import wraps
from inspect import signature
from time import sleep

import requests
from bs4 import BeautifulSoup

import utils

#####################
# Utility functions #
#####################

def refreshToken(credentials: dict) -> str:
    """
    Requests a new token from PageSeeder

    :param credentials: A dictionary like that found in the pageseeder section of ``config.json``
    :type credentials: dict
    :return: An access token for use with the PageSeeder API
    :rtype: str
    """
    with open('src/pstoken.json', 'w') as stream:
        print('[INFO][pageseeder] Requesting new access token...')

        url = f'https://{credentials["host"]}/ps/oauth/token'
        refresh_header = {
            'grant_type': 'client_credentials',
            'client_id': credentials['id'].lower(),
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

def token(credentials: dict) -> str:
    """
    Returns an access token for the PageSeeder configured in *credentials*.
    If existing token has expired or does not exist, refreshToken is called.

    :param credentials: A dictionary like that found in the pageseeder section of ``config.json``
    :type credentials: dict
    :return: An access token for use with the PageSeeder API
    :rtype: str
    """
    try:
        with open('src/pstoken.json', 'r') as stream:
            details = json.load(stream)
            token = details['token']
            issued = details['issued']

            if datetime.fromisoformat(issued) <= (datetime.now() - timedelta(hours=1)):
                token = refreshToken(credentials)
    except FileNotFoundError:
        token = refreshToken(credentials)
    except json.JSONDecodeError:
        token = refreshToken(credentials)
    return token

def auth(func):
    """
    A decorator that wraps a PageSeeder API function and provides default values for the kwargs 'host', 'member', 'group', and 'header'.

    :param func: A function to wrap
    :type func: function
    :return: A wrapped function
    :rtype: function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):

        credentials = utils.config()['pageseeder']
        
        defaults = {
            'host': f'https://{credentials["host"]}/ps/service',
            'member': credentials['username'],
            'group': credentials['group'],
            'header': {
                    'authorization': f'Bearer {token(credentials)}',
                    'Accept': 'application/json'
                }
        }

        for kw in signature(func).parameters:
            if kw not in kwargs and kw in defaults:
                kwargs[kw] = defaults[kw]
        return utils.handle(func)(*args, **kwargs)

    return wrapper

# global urimap
global _urimap
_urimap = {}

def urimap():
    """
    Returns value of default urimap if it has already been fetched. If not, it is fetched and returned.

    :Returns:
        Urimap of *website* directory at root of PageSeeder group
    """
    global _urimap
    if not _urimap:
        group = utils.config()["pageseeder"]["group"]
        websiteDirCheck = json.loads(search({
            'filters': f'pstype:folder,psfilename:website,psfolder:/ps/{group.replace("-","/")}'
        }))
        if websiteDirCheck['results']['result']:
            for field in websiteDirCheck['results']['result'][0]['fields']:
                if field['name'] == 'psid':
                    _urimap = get_urimap(field['value'])
        else:
            raise RuntimeError(f'Directory \'website\' not present at root of group {group}.')
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
def export(params={}, directory = False, host='', member='', header={}):
    """
    Begins export process for some URI and returns relevant thread ID
    """
    service = f'/members/~{member}/export' if directory else f'/members/~{member}/uris/{params["uri"]}/export'
    r = requests.get(host+service, headers=header, params=params)
    return r.text


@auth
def get_thread_progress(id, host='', group='', header={}):
    """
    Returns information about some PageSeeder process thread
    """
    service = f'/groups/{group}/threads/{id}/progress'
    r = requests.get(host+service, headers=header)
    return r.text


@auth
def get_thread_logs(id, host='', group='', header={}):
    """
    Returns information about some PageSeeder process thread
    """
    service = f'/groups/{group}/threads/{id}/logs'
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
def get_toc(uri, params={}, host='', group='', member='', header={}):
    """
    Output the partial TOC for a publication including a content document and its ancestors.
    If URI is not in a publication, output the TOC for the URI only with no publications.
    """
    service = f'/members/{member}/groups/{group}/uris/{uri}/toc'
    r = requests.get(host+service, params=params, headers=header)
    return r.text


@auth
def get_urimap(dir_uri):
    """
    Maps the directories in a URI to their URIs
    """
    urimap = {}
    uris = json.loads(get_uris(dir_uri, params={'type': 'folder'}))
    for uri in uris['uris']:
        urimap[uri['displaytitle']] = uri['id']
    return urimap


@auth
def search(params={}, host='', group='', header={}):
    service = f'/groups/{group}/search'
    r = requests.get(host+service, headers=header, params=params)
    return r.text


@auth
def resolve_group_refs(params={}, host='', group='', member='', header={}):
    service = f'/members/{member}/groups/{group}/resolverefs'
    r = requests.post(host+service, headers=header, params=params)
    return r.text


@auth
def loading_zone_upload(path, params={}, host='', group='', header={}):
    with open(path, 'rb') as stream:
        payload = stream.read()

    if 'group' not in params:
        params['group'] = group
    if 'filename' not in params and 'X-File-Name' not in header:
        params['filename'] = 'netdox-psml.zip'

    service = f'/ps/servlet/upload'
    r = requests.put(host+service, headers=header, params=params, data=payload)
    return r.text


@auth
def get_loading_zone(params={}, host='', group='', member='', header={}):
    service = f'/members/{member}/groups/{group}/loadingzone'
    r = requests.get(host+service, headers=header, params=params)
    return r.text


@auth
def unzip_loading_zone(path, params={}, host='', group='', member='', header={}):
    params['path'] = path
    service = f'/members/{member}/groups/{group}/loadingzone/unzip'
    r = requests.post(host+service, headers=header, params=params)
    return r.text


@auth
def load_loading_zone(params={}, host='', group='', member='', header={}):
    service = f'/members/{member}/groups/{group}/loadingzone/start'
    r = requests.post(host+service, headers=header, params=params)
    return r.text


@auth
def clear_loading_zone(params={}, host='', group='', member='', header={}):
    service = f'/members/{member}/groups/{group}/loadingzone/clear'
    r = requests.post(host+service, headers=header, params=params)
    return r.text


@auth
def zip_upload(path, uploadpath, host='', group='', header={}):
    loading_zone_upload(path, params={'file':'netdox-psml.zip'}, host='https://ps-netdox.allette.com.au', group=group, header=header)
    print('[INFO][upload] File sent successfully.')
    thread = BeautifulSoup(unzip_loading_zone('netdox-psml.zip', params={'deleteoriginal':'true'}), features = 'xml').thread
    while thread['status'] != 'completed':
        sleep(2)
        try:
            thread = BeautifulSoup(get_thread_progress(thread['id']), features = 'xml').thread
        except TypeError:
            print('[ERROR][upload] Upload failed. Clearing loading zone...')
            clear_loading_zone()
            return

    print('[INFO][upload] File unzipped. Loading files into PageSeeder.')
    return load_loading_zone(params={
        'folder': uploadpath,
        'overwrite': 'true',
        'overwrite-properties': 'true',
        'validate': 'false'
        })
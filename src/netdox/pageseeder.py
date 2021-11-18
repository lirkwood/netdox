"""
Used to interface with the PageSeeder REST API for numerous operations throughout Netdox's lifecycle.

Provides many various convenience functions for PageSeeder API actions, returning JSON where possible.
The decorator ``@auth`` injects default values and authentication details to the most of the functions in this script.
"""

import json
import logging
import os
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from functools import cache, wraps
from inspect import signature
from time import sleep

import requests
from bs4 import BeautifulSoup
from netdox import utils

logger = logging.getLogger(__name__)

logging.getLogger('urllib3').setLevel(logging.INFO)
logging.getLogger('spnego').setLevel(logging.INFO)

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
    with open(utils.APPDIR+ 'src/pstoken.json', 'w') as stream:
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
        with open(utils.APPDIR+ 'src/pstoken.json', 'r') as stream:
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
        # TODO remove handle functionality

    return wrapper

def uri_from_path(path: str) -> int:
    """
    Returns the URI of a PageSeeder object, from it's filepath.

    :param path: Path to object, relative to group root directory.
    :type path: str
    :return: The URI of the specified object,
    :rtype: int
    """
    path = path.strip('/')
    if '/' in path:
        pathlist = path.split('/')
        filename = pathlist[-1]
        folder = '/' + '/'.join(pathlist[:-1])
    else:
        filename = path
        folder = ''

    group = utils.config()["pageseeder"]["group"]
    dirCheck = json.loads(search({
        'filters': f'pstype:folder,psfilename:{filename},' +
                    f'psfolder:/ps/{group.replace("-","/")}{folder}'
    }))
    if dirCheck['results']['result']:
        for field in dirCheck['results']['result'][0]['fields']:
            if field['name'] == 'psid':
                return int(field['value'])

    raise FileNotFoundError(f"Failed to find object at path: '{path}'")

@cache
def urimap(
        path: str = 'website', 
        type: str = 'folder', 
        relationship: str = 'children'
    ) -> dict[str, str]:
    """
    Maps the names of the uris of type *type* in the folder *path* to their URIs.

    :param path: Path to the directory to map relative to group root directory, defaults to 'website'
    :type path: str, optional
    :param type: Type of files to map, defaults to 'folder'
    :type type: str, optional
    :param relationship: Relationship to *path* of URIs to return. One of: 
    'children', 'descendants', 'ancestors', 'ancestors-siblings', 'siblings'.
    :type relationship: str
    :raises FileNotFoundError: If the path is not present on PageSeeder.
    :return: A dictionary mapping filenames to URIs.
    :rtype: dict[str, str]
    """
    uris = get_uris(uri_from_path(path), params={
        'type': type,
        'relationship': relationship
    })
    return {
        uri['displaytitle']: uri['id'] for uri in 
        json.loads(uris)['uris']
    }


##############
# Sentencing #
##############

def sentence_uri(uri: str) -> date:
    """
    Adds two labels to the document on PageSeeder with the given URI,
    which indicates that the object has been sentenced and when.
    After 30 days of being sentenced the document will be archived.

    :param uri: The URI of the document to sentence.
    :type uri: str
    :return: The date *uri* will expire.
    :rtype: date
    """
    plus_thirty = date.today() + timedelta(days = 30)
    info = json.loads(get_uri(uri))
    labels = info['labels'] if 'labels' in info else []
    if 'stale' not in labels:
        labels.append(f'stale,expires-{plus_thirty}')
        patch_uri(uri, {'labels':','.join(labels)})
        logger.info(f"File '{info['title']}' is stale and has been sentenced.")
        return plus_thirty
    else:
        for label in labels:
            match = re.fullmatch(utils.expiry_date_pattern, label)
            if match:
                return date.fromisoformat(match['date'])
        raise RuntimeError(f'URI {uri} is marked stale but has no expiry date.')

def clear_sentence(uri: str) -> None:
    """
    Remove the sentence from the document with the given URI.

    :param uri: The URI of the document to clear the sentence of.
    :type uri: str
    """
    try:
        labels: list[str] = json.loads(get_uri(uri))['labels']
    except KeyError:
        return
    else:
        for label in labels:
            if label == 'stale' or re.fullmatch(utils.expiry_date_pattern, label):
                labels.remove(label)
        patch_uri(uri, {'labels':labels})


def sentenceStale(dir: str) -> dict[date, list[str]]:
    """
    Adds stale labels to any files present in *dir* on PageSeeder, but not locally.

    :param dir: The directory, relative to ``website/`` on PS or ``out/`` locally.
    :type dir: str
    :return: A dict of date objects mapped to uris which expire on that date.
    :rtype: dict[date, list[str]]
    """
    stale = defaultdict(list)
    today = date.today()
    group_path = f"/ps/{utils.config()['pageseeder']['group'].replace('-','/')}"
    
    if dir in urimap():
        local = utils.fileFetchRecursive(
            os.path.normpath(os.path.join(utils.APPDIR, 'out', dir)),
            relative = utils.APPDIR + 'out'
        )
        remote = json.loads(get_uris(urimap()[dir], params={
            'type': 'document',
            'relationship': 'descendants'
        }))

        for file in remote["uris"]:
            uri = file["id"]
            labels = file['labels'] if 'labels' in file else []
            commonpath = os.path.normpath(file["decodedpath"].split(f"{group_path}/website/")[-1])

            expiry = None
            for label in labels:
                match = re.fullmatch(utils.expiry_date_pattern, label)
                if match:
                    expiry = date.fromisoformat(match['date'])
            
            if commonpath in local and expiry is not None:
                clear_sentence(uri)

            elif commonpath not in local:
                if expiry and expiry <= today:
                    archive(uri)
                    logger.info(f"Archiving document '{file['title']}' as it is >=30 days stale.")
                elif expiry is not None:
                    stale[expiry].append(uri)
                else:
                    stale[sentence_uri(uri)].append(uri)
                    
    return stale

##########################
# PageSeeder API Servlet #
##########################

@auth
def get_default_docid(docid, params={}, header={}):
    """
    Returns the content of a document, from it's docid.
    """
    url = f'https://{utils.config()["pageseeder"]["host"]}/ps/docid/{docid}'
    return requests.get(url, headers=header, params=params)


###########################
# PageSeeder API Services #
###########################

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
def member_resource(zip, host='', group='', header='') -> requests.Response:
    """
    Returns a streamed response object containing a ZIP file found on PageSeeder.
    """
    service = f'/member-resource/~{group}/{zip}'
    return requests.get(host+service, headers=header, stream=True)


@auth
def put_group_resource(location: str, content: str, overwrite: bool, host='', group='', header=''):
    service = f'/groups/{"-".join(group.split("-")[:-1])}/resources'
    params = {'location': location, 'overwrite': str(overwrite).lower()}
    return requests.put(host+service, data=content, headers=header, params=params)


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
def get_group(host='', group='', header={}):
    """
    Gets a group
    """
    service = f'/groups/{group}'
    r = requests.get(host+service, headers=header)
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
    logger.info('File sent successfully.')
    thread = BeautifulSoup(unzip_loading_zone('netdox-psml.zip', params={'deleteoriginal':'true'}), features = 'xml').thread
    while thread['status'] != 'completed':
        sleep(2)
        try:
            thread = BeautifulSoup(get_thread_progress(thread['id']), features = 'xml').thread
        except TypeError:
            logger.error('Upload failed. Clearing loading zone...')
            clear_loading_zone()
            return

    logger.info('File unzipped. Loading files into PageSeeder.')
    return load_loading_zone(params={
        'folder': uploadpath,
        'overwrite': 'true',
        'overwrite-properties': 'true',
        'validate': 'false'
        })

if __name__ == '__main__':
    urimap()

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
from functools import lru_cache, wraps
from inspect import signature
from time import sleep
from typing import Iterable, Optional
from zipfile import ZipFile

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
    #TODO move this off disk
    with open(utils.APPDIR+ 'src/pstoken.json', 'w') as stream:
        url = f'https://{credentials["host"]}/ps/oauth/token'
        refresh_header = {
            'grant_type': 'client_credentials',
            'client_id': credentials['id'].lower(),
            'client_secret': credentials['secret']
        }

        r = requests.post(url, params=refresh_header)
        try:
            token = json.loads(r.text)['access_token']
        except KeyError:
            raise ValueError(f'Unexpected response when requesting token: {r.text}')
        else:
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
    Returns the URI of a PageSeeder folder, from it's filepath.

    :param path: Path to folder, relative to group root directory.
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
    if dirCheck['results']['totalResults'] > 0:
        for field in dirCheck['results']['result'][0]['fields']:
            if field['name'] == 'psid':
                return int(field['value'])

    raise FileNotFoundError(f"Failed to find object at path: '{path}'")

@lru_cache(maxsize = None)
def urimap(
        path: str = 'website', 
        type: str = 'folder', 
        relationship: str = 'children'
    ) -> dict[str, int]:
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
    :rtype: dict[str, int]
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

def sentence_uri(uri: str) -> date: # TODO remove this function
    """
    DEPRECATED
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
        
        display_name = info['title'] if 'title' in info else f'URI:{uri}'
        logger.info(f"File '{display_name}' is stale and has been sentenced.")
        
        return plus_thirty
    else:
        for label in labels:
            match = re.fullmatch(utils.expiry_date_pattern, label)
            if match:
                return date.fromisoformat(match['date'])
        labels.append(f'expires-{plus_thirty}')
        patch_uri(uri, {'labels':','.join(labels)})
        return plus_thirty

def sentence_uris(uris: list[str], assignee: str) -> None:
    """Sentences documents with URIs in the list to be archived, after approval."""
    filter = ''
    for uri in uris:
        filter += f'psid:{uri},'
        
    batch_document_action('addworkflow', {
        'filters': filter,
        'action.assignedto': assignee,
        'action.due': str(date.today() + timedelta(days = 30)),
        'action.status': 'Initiated'
    })

def clear_sentence(uri: str) -> None: # TODO remove this function
    """
    DEPRECATED
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

def clear_sentences(uris: list[str]) -> None:
    """Removes the sentences from documents with URIs in the list."""
    logger.debug(f'Clearing sentences from {len(uris)} documents.')
    filter = ''
    for uri in uris:
        filter += f'psid:{uri},'

    batch_document_action('addworkflow', {
        'filters': filter,
        'action.assignedto': 'netdox website', #TODO get assignee from config
        'action.due': '',
        'action.status': 'Terminated'
    })    


def statusFromFile(file: dict[str, str]) -> Optional[str]:
    """Returns the workflow status from the dict describing a file 
    returned by pageseeder from a search, if it is assigned to the correct user."""
    if (
        'psstatus' in file and 'psassignedto' in file and
        file['psassignedto'] == 'netdox website'
    ):
        # TODO get assignee from config file
        return file['psstatus']
    return None

def sentenceStale(dir: str) -> dict[date, list[str]]:
    """
    Adds stale labels to any files present in *dir* on PageSeeder, but not locally.

    :param dir: The directory, relative to ``website/`` on PS or ``out/`` locally.
    :type dir: str
    :return: A dict of date objects mapped to uris which expire on that date.
    :rtype: dict[date, list[str]]
    """
    stale: defaultdict[date, list[str]] = defaultdict(list)
    group_path = f"/ps/{utils.config()['pageseeder']['group'].replace('-','/')}"
    member = json.loads(get_self())
    
    if dir in urimap():
        try:
            local = utils.path_list(
                os.path.normpath(os.path.join(utils.APPDIR, 'out', dir)),
                relative = utils.APPDIR + 'out'
            )
        except FileNotFoundError:
            logger.error(f'No such directory locally to detect stale items in: {dir}')
            return {}
        remote = search_parsed(params = {
            'filters': f'pstype:document,psancestor:{group_path}/website/{dir}'
        })

        sentence = []
        clear = []
        for file in remote:
            uri = file["psid"]
            status = statusFromFile(file)
            commonpath = os.path.normpath(os.path.join(
                file['psfolder'].split(f"{group_path}/website/", 1)[-1], file['psfilename']
            ))
            logger.debug(f'{file} --- status {status}')

            # File no longer stale and is marked stale
            if commonpath in local and status in ('Initiated', 'Approved'):
                clear.append(uri)

            elif commonpath not in local:
                # File is stale and has been approved for archival
                if status == 'Approved':
                    archive(uri)
                    title = file['title'] if 'title' in file else f'(URI={file["id"]})'
                    logger.info(f"Archiving document '{title}' as it has been approved.")

                # File is stale and has no been marked stale yet
                elif status is None:
                    logger.debug(f'Sentencing new file: {file["psfilename"]}')
                    sentence.append(uri)
                    
        if len(clear) > 0:
            clear_sentences(clear)
        if len(sentence) > 0:
            sentence_uris(sentence, member['id'])

    return stale

def findStale(dirs: Iterable[str]) -> dict[date, set[str]]:
    """
    Finds any stale documents in the provided directories (relative to the output dir).

    :param dirs: Some paths to search for stale documents.
    Must exist on PageSeeder in the web context aswell.
    :type dirs: Iterable[str]
    :return: A dict mapping a date to a list of URIs that will expire on that date.
    :rtype: dict[date, list[str]]
    """
    stale: dict[date, set[str]] = {}
    for folder in dirs:
        for expiry, uri_list in sentenceStale(folder).items():
            if expiry not in stale:
                stale[expiry] = set()
            stale[expiry] |= set(uri_list)
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

@auth
def get_default_uriid(uriid, params={}, header={}):
    """
    Returns the content of a document, from it's uriid.
    """
    url = f'https://{utils.config()["pageseeder"]["host"]}/ps/uri/{uriid}'
    return requests.get(url, headers=header, params=params)

@auth
def loading_zone_upload(path, params={}, host='', group='', header={}):
    with open(path, 'rb') as stream:
        payload = stream.read()

    if 'group' not in params:
        params['group'] = group
    if 'filename' not in params and 'X-File-Name' not in header:
        params['filename'] = 'netdox-psml.zip'

    url = f'https://{utils.config()["pageseeder"]["host"]}/ps/servlet/upload'
    r = requests.put(url, headers=header, params=params, data=payload)
    return r.text

@auth
def member_resource(file: str, host='', group='', header='') -> requests.Response:
    """
    Returns a streamed response object containing a ZIP file found on PageSeeder.
    """
    url = f'https://{utils.config()["pageseeder"]["host"]}/ps/member-resource/{group}/{file}'
    return requests.get(url, headers=header, stream=True)

@auth
def download_dir(path: str, outpath: str, timeout: int = 60000) -> str:
    """
    Downloads a directory from PageSeeder to the local machine.
    Times out after *timeout* milliseconds.

    :param path: Path on PageSeeder to download, relative to the group root.
    :type path: str
    :param outpath: Where to unzip the downloaded directory on the local machine.
    :type outpath: str
    :param timeout: Number of milliseconds to timeout after, defaults to 5000
    :type timeout: int, optional
    :return: The path to the downloaded directory
    :rtype: str
    """
    _thread = export({
        'path': f'/{utils.config()["pageseeder"]["group"].replace("-","/")}/{path}'
    }, directory = True)
    thread = BeautifulSoup(_thread, 'xml').thread
    last_thread = thread
    try:
        while thread['status'] in ('initialised', 'inprogress'):
            sleep(0.5)
            last_thread = thread
            thread = BeautifulSoup(get_thread_progress(thread['id']), 'xml').thread
    except KeyError as err:
        print(err)
        raise AttributeError('Download thread never had status "completed".\n' + str(thread))
    except TypeError:
        assert thread is None, 'Strange fail state: TypeError when accessing thread like dict.'
        raise AttributeError('Download thread never had status "completed" (thread is None).\n'
            + str(last_thread))
    
    if thread['status'] == 'failed':
        try:
            message = thread.message.string
        except Exception:
            message = '[ERROR MSG NOT FOUND]'
        finally:
            raise RuntimeError(f'Failed to export directory at "{path}" from PageSeeder.'
                + f' Message: "{message}"')

    elif thread['status'] != 'completed':
        logger.warning('Unknown thread final thread status while downloading '
            + f'directory at "{path}" from PageSeeder: "{thread["status"]}"')

    if os.path.exists(outpath) and not os.path.isdir(outpath):
        raise FileExistsError('File object exists at output path, is not a directory.')
    elif not os.path.exists(outpath):
        os.mkdir(outpath)

    zip_path = outpath + '.zip'
    with member_resource(thread.zip.text) as zip:
        zip.raise_for_status()
        with open(zip_path, 'wb') as stream:
            for chunk in zip.iter_content(8192):
                stream.write(chunk)

    ZipFile(zip_path).extractall(outpath)
    os.remove(zip_path)
                
    return outpath

###########################
# PageSeeder API Services #
###########################

def get_version(host, **kwargs):
    """
    Returns the version of a PageSeeder server.
    """
    soup = BeautifulSoup(
        requests.get(f'https://{host}/ps/service/version', **kwargs).text, 'xml')
    return soup.find('version')['string']

@auth
def get_self(host = '', header={}):
    """Returns details of the currently authenticated member."""
    r = requests.get(host+'/self', headers=header)
    return r.text

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
def search_parsed(params={}, host='', group='', header={}) -> list[dict[str, str]]:
    """
    Like search but parses each result into a map of its fields.
    """
    resp = json.loads(search(params=params, host=host, group=group, header=header))
    try:
        results: list[dict] = resp['results']['result']
        if 'page' not in params:
            current_page = int(resp['results']['page'])
            while int(resp['results']['totalPages']) > current_page:
                current_page += 1
                resp = json.loads(search(params | {'page': current_page}, host=host, group=group, header=header))
                results.extend(resp['results']['result'])
        parsed_results = []
        for result in results:
            parsed_result = {}
            for field in result['fields']:
                parsed_result[field['name']] = field['value']
            parsed_results.append(parsed_result)

        return parsed_results
                
    except KeyError:
        raise ValueError('Bad response from search; failed to parse results.')


@auth
def resolve_group_refs(params={}, host='', group='', member='', header={}):
    service = f'/members/{member}/groups/{group}/resolverefs'
    r = requests.post(host+service, headers=header, params=params)
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
    loading_zone_upload(path, params={'file':'netdox-psml.zip'}, host=host, group=group, header=header)
    logger.info('File sent successfully.')
    thread = BeautifulSoup(unzip_loading_zone('netdox-psml.zip', params={'deleteoriginal':'true'}), features = 'xml').thread
    while thread and thread['status'] != 'completed':
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


@auth
def get_uri_history(uri='', params={}, host='', group='', header={}):
    service = f'/groups/{group}/uris/{uri}/history'
    r = requests.get(host+service, params=params, headers=header)
    return r.text

@auth
def get_uris_history(params={}, host='', group='', header={}):
    service = f'/groups/{group}/uris/history'
    r = requests.get(host+service, params=params, headers=header)
    return r.text

@auth
def batch_document_action(action, params={}, host='', group='', member='', header={}):
    service = f'/members/{member}/groups/{group}/batch/uri/{action}/search'
    r = requests.post(host+service, params=params, headers=header)
    return r.text

if __name__ == '__main__':
    urimap()

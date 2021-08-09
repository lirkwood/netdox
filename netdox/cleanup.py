"""
This script is used for preparing outgoing data for the PageSeeder upload.

One of its primary uses is parsing the output of :ref:`file_screenshot`.
This involves converting all the screenshots from PNG files to JPGs,
saving screenshots which are to be overwritten in the *screenshot_history* folder,
and generating placeholder images for websites which Netdox failed to screenshot.
"""

import json
import os
import re
import shutil
from datetime import date, datetime, timedelta

from PIL import Image, UnidentifiedImageError

import pageseeder
import utils

stale_pattern = re.compile(r'expires-(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})')

@utils.handle
def sentenceStale() -> dict:
    """
    The purpose of this function is to mark documents which are present on PageSeeder but not in the local upload context as *stale* (out of date/nonexistent).
    Any documents which exist exclusively on PageSeeder have a document label applied matching a string like ``expires-on-<date + 30 days>``.
    Should a document exist that was sentenced to expire today or in the past, Netdox will archive it.

    :return: A dictionary of domains newly marked as stale
    :rtype: dict
    """
    today = datetime.now().date()
    group_path = f"/ps/{utils.config()['pageseeder']['group'].replace('-','/')}"
    stale = {}
    # for every folder in context on pageseeder
    for folder, folder_uri in pageseeder.urimap().items():
        # get all files descended from folder
        remote = json.loads(pageseeder.get_uris(folder_uri, params={
            'type': 'document',
            'relationship': 'descendants'
        }))

        # if folder exists in upload
        if os.path.exists(os.path.join('out', folder)) and folder not in ('config', 'review', 'screenshot_history'):
            # get all files in given folder in upload
            local = utils.fileFetchRecursive(os.path.join('out', folder))

            for file in remote["uris"]:
                commonpath = file["decodedpath"].split(f"{group_path}/website/")[-1]
                uri = file["id"]
                if 'labels' in  file: 
                    labels = ','.join(file['labels'])
                    marked_stale = re.search(stale_pattern, labels)
                else:
                    labels = ''
                    marked_stale = False

                if marked_stale:
                    expiry = date.fromisoformat(marked_stale['date'])
                else:
                    expiry = None
                
                if os.path.normpath(os.path.join('out', commonpath)) not in local:
                    if marked_stale:
                        if expiry <= today:
                            pageseeder.archive(uri)
                        else:
                            stale[uri] = marked_stale['date']
                    else:
                        plus_thirty = today + timedelta(days = 30)
                        if labels: labels += ','
                        labels += f'stale,expires-{plus_thirty}'
                        pageseeder.patch_uri(uri, {'labels':labels})
                        print(f'[INFO][cleanup] File {commonpath} is stale and has been sentenced.')
                        stale[uri] = str(plus_thirty)
                # if marked stale but exists locally
                else:
                    if marked_stale:
                        labels = re.sub(stale_pattern, '', labels) # remove expiry label
                        labels = re.sub(r',,',',', labels) # remove double commas
                        labels = re.sub(r',$','', labels) # remove trailing commas
                        labels = re.sub(r'^,','', labels) # remove leading commas
                        pageseeder.patch_uri(uri, {'labels':labels})
    return {k: v for k, v in sorted(stale.items(), key = lambda item: item[1])}
            

# best guess at the transformation PageSeeder applies
def alnum(string: str) -> str:
    """
    Performs the same character substitutions PageSeeder applies to filenames.

    :param string: The string to perform the transformation on
    :type string: str
    :return: The input string with characters in ``[/\\?%*:|<>^]`` or ``[^\x00-\x7F]`` substituted for underscores.
    :rtype: str
    """
    string = re.sub(r'[/\\?%*:|<>^]', '_', string)
    return re.sub(r'[^\x00-\x7F]', '_', string)


def pre_upload():
    """
    The main pre-upload cleanup flow, used to prepare for upload and detect old files on PageSeeder.
    
    Adds the *stale* domains to ``review.json`` in order for them to be shown in the status update (see :ref:`file_status`).
    """
    global today
    today = str(datetime.now().date())

    # archive last review if exist
    try:
        pageseeder.archive(pageseeder.urimap()['review'])
    except KeyError:
        pass

    stale = sentenceStale()
    if stale:
        with open('src/stale.json', 'w') as stream:
            stream.write(json.dumps(stale, indent=2))

    pageseeder.clear_loading_zone()


def post_upload():
    """
    Main post-upload cleanup flow, currently does nothing.
    """
    pass



if __name__ == '__main__':
    post_upload()

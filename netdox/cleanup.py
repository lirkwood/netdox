"""
This script is used for preparing outgoing data for the PageSeeder upload.

One of its primary uses is parsing the output of :ref:`file_screenshot`.
This involves converting all the screenshots from PNG files to JPGs,
saving screenshots which are to be overwritten in the *screenshot_history* folder,
and generating placeholder images for websites which Netdox failed to screenshot.
"""

from datetime import timedelta, datetime, date
from PIL import Image, UnidentifiedImageError
import re, os, json, shutil
import pageseeder, utils


def parseReview():
    """
    Parses the ``review.json`` file returned by ``screenshotCompare.js``.

    Every screenshot which will be overwritten by the PNG to JPG conversion is saved in the ``screenshot_history`` directory under a dated folder.
    This function also deletes any 'diff overlay' images that have <10% different pixels, as specified in ``review.json``.
    """
    global today
    if not os.path.exists(f'out/screenshot_history/{today}'):
        os.mkdir(f'out/screenshot_history/{today}')
    with open('src/review.json','r') as stream:
        review = json.load(stream)
        # check if any domains occur in multiple categories
        all_domains = list(review['no_ss'].keys()) + review['no_base'] + review['imgdiff'] + review['nodiff']
        if len(all_domains) > len(list(dict.fromkeys(all_domains))):
            print('[WARNING][cleanup] Duplication detected in review.json')
        # save base images that will be overwritten
        for domain in (review['imgdiff'] + list(review['no_ss'].keys())):
            try:
                pngName = f"{domain.replace('.','_')}.png"
                shutil.copyfile(f'/etc/ext/base/{pngName}', f'out/screenshot_history/{today}/{pngName}')
            except FileNotFoundError:
                pass
        # delete unnecessary imgdiff overlay images (e.g. <10% pixel diff)
        for domain in review['nodiff']:
            try:
                pngName = f"{domain.replace('.','_')}.png"
                os.remove(f'out/review/{pngName}')
            except FileNotFoundError:
                pass


# converts every file in a dir from png to 1024x576 jpg
def png2jpg(path):
    """
    Converts all PNG images in a directory to 1024x576 JPGs.

    :Args:
        A string path to a directory containing some image files.. 
    """
    try:
        for file in os.scandir(path):
            try:
                img = Image.open(path +'/'+ file.name)
                img_small = img.resize((1024, 576)).convert('RGB')
                os.remove(file)
                outfile = file.name.replace('.png','.jpg')
                img_small.save(path +'/'+ outfile)

            except UnidentifiedImageError:
                print(f'[WARNING][cleanup] Cannot open {file.name} as image file.')
    except FileNotFoundError:
        print(f'[WARNING][cleanup] Path {path} does not exist.')


@utils.handle
def placeholders():
    """
    Generates placeholder images for domains with no screenshot locally or on PageSeeder.

    For any website which Netdox was unable to screenshot, this function checks the set of screenshots on PageSeeder.
    If an image of that website already exists (be it placeholder or screenshot), no placeholder will be generated.
    """
    # if puppeteer failed to screenshot and no existing screen on pageseeder, copy placeholder
    try:
        pageseeder_screens = pageseeder.get_files(pageseeder.urimap()['screenshots'])  # get list of screenshots on pageseeder
    except KeyError:
        pageseeder_screens = []

    with open('src/review.json','r') as stream:
        no_ss = json.load(stream)['no_ss']
        for domain in no_ss:
            jpgName = f"{domain.replace('.','_')}.jpg"
            if jpgName not in pageseeder_screens:
                shutil.copyfile('src/placeholder.jpg', f'out/screenshots/{jpgName}')


stale_pattern = re.compile(r'expires-(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})')

@utils.handle
def sentenceStale():
    """
    The purpose of this function is to mark documents which are present on PageSeeder but not in the local upload context as *stale* (out of date/nonexistent).
    Any documents which exist exclusively on PageSeeder have a document label applied matching a string like ``expires-on-<date + 30 days>``.
    Should a document exist that was sentenced to expire today or in the past, Netdox will archive it.

    :Returns:
        A dictionary of any URIs that were newly marked as stale, sorted by date they expire on.
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
        if os.path.exists(f'out/{folder}') and folder not in ('config', 'review', 'screenshot_history'):
            # get all files in given folder in upload
            local = utils.fileFetchRecursive(f'out/{folder}')

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
                
                if f'out/{commonpath}' not in local:
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
def alnum(string):
    """
    Performs the same character substitutions PageSeeder applies to filenames.
    """
    string = re.sub(r'[/\\?%*:|<>^]', '_', string)
    return re.sub(r'[^\x00-\x7F]', '_', string)


def pre_upload():
    """
    The main pre-upload cleanup flow, used to prepare for upload and detect old files on PageSeeder.

    Runs ``png2jpg`` on the *screenshots*, *review*, and *screenshot_history* directories.
    Also attempts to archive the *review* directory on PageSeeder from the last refresh, if it exists.
    Finally, adds the *stale* domains to ``review.json`` in order for them to be shown in the status update (see :ref:`file_status`).
    """
    global today
    today = str(datetime.now().date())

    # act on values in review.json
    parseReview()

    # overwrite base images
    try:
        shutil.rmtree('/etc/ext/base')
    except FileNotFoundError:
        pass
    
    shutil.copytree('out/screenshots', '/etc/ext/base')

    # scale down all exported img files
    png2jpg('out/screenshots')
    png2jpg('out/review')
    png2jpg(f'out/screenshot_history/{today}')

    # generate placeholders where there is no ss locally or on ps
    placeholders()

    # archive last review if exist
    try:
        pageseeder.archive(pageseeder.urimap()['review'])
    except KeyError:
        pass

    stale = sentenceStale()
    if stale:
        with open('src/review.json', 'r') as stream:
            review = json.load(stream)
        with open('src/review.json', 'w') as stream:
            review['stale'] = stale
            stream.write(json.dumps(review, indent=2))


def post_upload():
    """
    Main post-upload cleanup flow, currently just starts a resolve xrefs process for upload group.
    """
    pageseeder.resolve_group_refs()



if __name__ == '__main__':
    post_upload()
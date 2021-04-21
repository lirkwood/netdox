from datetime import timedelta, datetime, date
from PIL import Image, UnidentifiedImageError
from bs4 import BeautifulSoup
import re, os, json, shutil
import ps_api, utils


def review():
    """
    Perform various actions based on a domains value in review.json
    """
    global today
    os.mkdir(f'/opt/app/out/screenshot_history/{today}')
    with open('src/review.json','r') as stream:
        review = json.load(stream)
        for domain in review:
            try:
                if review[domain] == 'imgdiff' or review[domain].startswith('no_ss'):
                    pngName = f"{domain.replace('.','_')}.png"
                    shutil.copyfile(f'/etc/ext/base/{pngName}', f'/opt/app/out/screenshot_history/{today}/{pngName}')
                elif review[domain] == 'nodiff':
                    pngName = f"{domain.replace('.','_')}.png"
                    os.remove(f'/opt/app/out/review/{pngName}')
            except FileNotFoundError:
                pass


# converts every file in a dir from png to 1024x576 jpg
def png2jpg(path):
    """
    Converts png images in some dir to fixed size jpgs
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
                print(f'[WARNING][cleanup.py] Cannot open {file.name} as image file.')
    except FileNotFoundError:
        print(f'[WARNING][cleanup.py] Path {path} does not exist.')


@utils.handle
def placeholders():
    """
    Generates placeholder images for domains with no screenshot locally or on PageSeeder
    """
    # if puppeteer failed to screenshot and no existing screen on pageseeder, copy placeholder
    try:
        existing_screens = ps_api.get_files(ps_api.urimap['screenshots'])  # get list of screenshots on pageseeder
    except KeyError:
        existing_screens = []

    with open('src/review.json','r') as stream:
        review = json.load(stream)
        for domain in review:
            jpgName = f"{domain.replace('.','_')}.jpg"
            if jpgName not in existing_screens and review[domain].startswith('no_ss:'):
                shutil.copyfile('src/placeholder.jpg', f'out/screenshots/{jpgName}')


@utils.handle
def sentenceStale():
    """
    Adds 30-day timer to files present on pageseeder but not locally
    """
    today = datetime.now().date()
    for folder in ps_api.urimap:
        folder_uri = ps_api.urimap[folder]
        remote = BeautifulSoup(ps_api.get_uris(folder_uri, params={'type': 'document'}), features='xml')
        if os.path.exists(f'out/{folder}'):
            # alnum filenames for every file in local version of folder that is a file (not dir)
            local = [alnum(file) for file in os.listdir(f'out/{folder}') if os.path.isfile(os.path.join(f'out/{folder}', file))]

            for file in remote("uri"):
                filename = file["decodedpath"].split('/')[-1]
                uri = file["id"]
                if filename not in local:
                    if file.labels:
                        labels = file.labels.string

                    marked_stale = re.search(r'expires-(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})', labels)
                    if marked_stale:
                        expiry = date(*marked_stale['date'].split('-'))
                        if expiry <= today:
                            ps_api.archive(uri)
                    else:
                        if labels:
                            labels += ','
                        else:
                            labels = ''
                        labels += f'expires-{today + timedelta(days = 30)}'
                        ps_api.patch_uri(uri, {'labels':labels})
            

# best guess at the transformation PageSeeder applies
def alnum(string):
    string = re.sub(r'[/\\?%*:|<>^]', '_', string)
    return re.sub(r'[^\x00-\x7F]', '_', string)


@utils.critical
def clean():
    global today
    today = str(datetime.now().date())

    # act on values in review.json
    review()

    # overwrite base images
    try:
        shutil.rmtree('/etc/ext/base')
    except FileNotFoundError:
        pass
    
    shutil.copytree('/opt/app/out/screenshots', '/etc/ext/base')

    # scale down all exported img files
    png2jpg('/opt/app/out/screenshots')
    png2jpg('/opt/app/out/review')
    png2jpg(f'/opt/app/out/screenshot_history/{today}')

    # generate placeholders where there is no ss locally or on ps
    placeholders()

    # archive last review if exist
    try:
        ps_api.archive(ps_api.urimap['review'])
    except KeyError:
        pass

    sentenceStale()
    # for folder in ps_api.urimap:
    #     ps_api.version(ps_api.urimap[folder])
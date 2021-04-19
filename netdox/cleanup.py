from PIL import Image, UnidentifiedImageError
from bs4 import BeautifulSoup
from datetime import datetime
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
@utils.handle
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
            if (jpgName not in existing_screens) and review[domain].startswith('no_ss'):
                shutil.copyfile('src/placeholder.jpg', f'out/screenshots/{jpgName}')


@utils.handle
def sentenceStale():
    """
    Adds 30-day timer to files present on pageseeder but not locally
    """
    stale = set()
    for folder in ps_api.urimap:
        folder_uri = ps_api.urimap[folder]
        remote = BeautifulSoup(ps_api.get_uris(folder_uri, params={'type': 'document'}), features='xml')
        if os.path.exists(f'out/{folder}'):
            _local = os.listdir(f'out/{folder}')
            local = []
            for file in _local:
                local.append(alnum(file))

            for file in remote("uri"):
                filename = alnum(file["decodedpath"].split('/')[-1])

                if filename not in local:
                    labels = file.labels.string
                    if not re.search('expires-[0-9]{4}-[0-9]{2}-[0-9]{2}', labels):
                        stale.add(filename)
            

def alnum(string):
    return re.sub(r'[^a-zA-Z0-9 .]', '', string)


@utils.critical
def clean():
    global today
    today = str(datetime.now().date())

    # act on values in review.json
    review()

    # overwrite base images
    shutil.rmtree('/etc/ext/base')
    shutil.copytree('/opt/app/out/screenshots', '/etc/ext/base')

    # scale down all exported img files
    png2jpg('/opt/app/out/screenshots')
    png2jpg('/opt/app/out/review')
    png2jpg(f'/opt/app/out/screenshot_history/{today}')

    # generate placeholders where there is no ss locally or on ps
    placeholders()
    ps_api.archive(ps_api.urimap['review'])

    # stale = sentenceStale()
    # for folder in ps_api.urimap:
    #     ps_api.version(ps_api.urimap[folder])
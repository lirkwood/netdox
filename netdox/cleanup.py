from PIL import Image, UnidentifiedImageError
from bs4 import BeautifulSoup
from datetime import datetime
import re, os, json, shutil
import ps_api, utils


@utils.handle
def getUrimap(dir_uri):
    """
    Generates dict with files in some dir as keys and their uris as values
    """
    urimap = {}
    soup = BeautifulSoup(ps_api.get_uris(dir_uri, params={'type': 'folder'}), 'lxml')
    for uri in soup.find_all('uri'):
        urimap[uri.displaytitle.string] = uri['id']
    
    return urimap


def screenshotHistory():
    """
    If screenshotCompare found a different image or couldnt ss, save the base image as it will be overwritten.
    """
    global today
    os.mkdir(f'/opt/app/out/screenshot_history/{today}')
    with open('src/review.json','r') as stream:
        review = json.load(stream)
        for image in review:
            if review[image] == 'imgdiff' or review[image].startswith('no_ss'):
                try:
                    shutil.copyfile(f'/etc/ext/base/{image}', f'/opt/app/out/screenshot_history/{today}/{image}')
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
        existing_screens = ps_api.get_files(urimap['screenshots'])  # get list of screenshots on pageseeder
    except KeyError:
        existing_screens = []

    with open('src/review.json','r') as stream:
        review = json.load(stream)
        for png in review:
            jpg = png.replace('.png','.jpg')
            if (jpg not in existing_screens) and review[png].startswith('no_ss'):
                shutil.copyfile('src/placeholder.jpg', f'out/screenshots/{jpg}')


@utils.handle
def compareFilesets():
    """
    Archives files present on pageseeder but not locally
    """
    for folder in urimap:
        folder_uri = urimap[folder]
        remote = BeautifulSoup(ps_api.get_uris(folder_uri, params={'type': 'document'}), features='xml')
        if os.path.exists(f'out/{folder}'):
            _local = os.listdir(f'out/{folder}')
            local = []
            for file in _local:
                local.append(alnum(file))

            for file in remote("uri"):
                filename = alnum(file["decodedpath"].split('/')[-1])
                uri = file["id"]

                if filename not in local:
                    ps_api.archive(uri)
            

def alnum(string):
    return re.sub(r'[^a-zA-Z0-9 .]', '', string)


@utils.handle
def clean():
    global urimap
    urimap = getUrimap('375156')
    global today
    today = str(datetime.now().date())

    try:
        screenshotHistory()
    except Exception as e:
        raise e
    else:
        shutil.rmtree('/etc/ext/base')
        shutil.copytree('/opt/app/out/screenshots', '/etc/ext/base')

    png2jpg('/opt/app/out/screenshots')
    png2jpg(f'/opt/app/out/screenshot_history/{today}')

    placeholders()
    compareFilesets()
    for folder in urimap:
        ps_api.version(urimap[folder])
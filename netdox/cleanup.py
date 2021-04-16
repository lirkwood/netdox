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


def cleanReview():
    with open('src/review.json','r') as stream:
        review = json.load(stream)
        for image in os.scandir('/opt/app/out/review'):
            # could potentially not match if domain has underscore :/
            if image.name.replace('.png','').replace('_','.') not in review:
                os.remove(image)

def screenshotHistory():
    """
    If screenshotCompare found a different image or couldnt ss, save the base image as it will be overwritten.
    """
    global today
    os.mkdir(f'/opt/app/out/screenshot_history/{today}')
    with open('src/review.json','r') as stream:
        review = json.load(stream)
        for domain in review:
            if review[domain] == 'imgdiff' or review[domain].startswith('no_ss'):
                pngName = f"{domain.replace('.','_')}.png"
                try:
                    shutil.copyfile(f'/etc/ext/base/{pngName}', f'/opt/app/out/screenshot_history/{today}/{pngName}')
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
        for domain in review:
            jpgName = f"{domain.replace('.','_')}.jpg"
            if (jpgName not in existing_screens) and review[domain].startswith('no_ss'):
                print(f'[INFO][cleanup.py] Generated placeholder image for {jpgName}')
                shutil.copyfile('src/placeholder.jpg', f'out/screenshots/{jpgName}')


@utils.handle
def sentenceStale():
    """
    Adds 30-day timer to files present on pageseeder but not locally
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


@utils.critical
def clean():
    global urimap
    urimap = getUrimap('375156')
    global today
    today = str(datetime.now().date())

    # save any base imgs about to be overwritten
    cleanReview()
    screenshotHistory()
    # overwrite
    shutil.rmtree('/etc/ext/base')
    shutil.copytree('/opt/app/out/screenshots', '/etc/ext/base')

    # scale down all exported img files
    png2jpg('/opt/app/out/screenshots')
    png2jpg('/opt/app/out/review')
    png2jpg(f'/opt/app/out/screenshot_history/{today}')

    # generate placeholders where there is no ss locally or on ps
    placeholders()

    # sentenceStale()
    # for folder in urimap:
    #     ps_api.version(urimap[folder])
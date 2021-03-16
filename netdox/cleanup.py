from PIL import Image, UnidentifiedImageError
import os, json, shutil

from bs4 import BeautifulSoup
import ps_api

def getUrimap():
    urimap = {}
    # URI of website folder = 375156
    soup = BeautifulSoup(ps_api.get_uri('375156', 'folder'))
    for uri in soup.find_all('uri'):
        urimap[uri.displaytitle.string] = uri['id']
    
    return urimap

global urimap
urimap = getUrimap()

# converts every file in a dir from png to 1024x576 jpg
def png2jpg(path):
    for file in os.scandir(path):
        try:
            img = Image.open(path +'/'+ file.name)
            img_small = img.resize((1024, 576)).convert('RGB')
            os.remove(file)
            outfile = file.name.replace('.png','.jpg')
            img_small.save(path +'/'+ outfile)

        except UnidentifiedImageError:
            print(f'[WARNING][cleanup.py] Cannot open {file.name} as image file.')


def placeholders():
    # if puppeteer failed to screenshot and no existing screen on pageseeder, copy placeholder
    existing_screens = ps_api.get_files(urimap['screenshots'])  # get list of screenshots on pageseeder
    with open('src/review.json','r') as stream:
        review = json.load(stream)
        for path in review:
            if (path.split('/')[-1] not in existing_screens) and review[path].startswith('no_ss'):
                shutil.copyfile('src/placeholder.jpg', path)


def clean():
    png2jpg('out/screenshots')
    placeholders()
    # for folder in urimap:
    #     ps_api.version(urimap[folder])

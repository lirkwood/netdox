from PIL import Image, UnidentifiedImageError
import re, os, json, shutil

from bs4 import BeautifulSoup
import ps_api

def getUrimap():
    urimap = {}
    # URI of website folder = 375156
    soup = BeautifulSoup(ps_api.get_uris('375156', params={'type': 'folder'}), 'lxml')
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
        for png in review:
            jpg = png.replace('.png','.jpg')
            if (jpg not in existing_screens) and review[png].startswith('no_ss'):
                shutil.copyfile('src/placeholder.jpg', f'out/screenshots/{jpg}')


def compareFilesets():
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


def clean():
    try:
        png2jpg('out/screenshots')
    except Exception as e:
        print('[ERROR][cleanup.py] Converting screenshots to small jpg failed:')
        print(e)
        print('[ERROR][cleanup.py] ****END****')

    try:
        placeholders()
    except Exception as e:
        print('[ERROR][cleanup.py] Generating placeholders failed:')
        print(e)
        print('[ERROR][cleanup.py] ****END****')

    try:
        compareFilesets()
    except Exception as e:
        print('[ERROR][cleanup.py] Archiving old documents on PageSeeder failed:')
        print(e)
        print('[ERROR][cleanup.py] ****END****')
    
    for folder in urimap:
        try:
            ps_api.version(urimap[folder])
        except Exception as e:
            print(f'[ERROR][cleanup.py] Versioning folder "{folder}" failed:')
            print(e)
            print('[ERROR][cleanup.py] ****END****')

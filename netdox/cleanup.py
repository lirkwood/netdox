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
        # check if any domains occur in multiple categories
        all_domains = list(review['no_ss'].keys()) + review['no_base'] + review['imgdiff'] + review['nodiff']
        if len(all_domains) > len(list(dict.fromkeys(all_domains))):
            print('[WARNING][cleanup.py] Duplication detected in review.json')
        # save base images that will be overwritten
        for domain in (review['imgdiff'] + list(review['no_ss'].keys())):
            try:
                pngName = f"{domain.replace('.','_')}.png"
                shutil.copyfile(f'/etc/ext/base/{pngName}', f'/opt/app/out/screenshot_history/{today}/{pngName}')
            except FileNotFoundError:
                pass
        # delete unnecessary imgdiff overlay images (e.g. <10% pixel diff)
        for domain in review['nodiff']:
            try:
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
        pageseeder_screens = ps_api.get_files(ps_api.urimap['screenshots'])  # get list of screenshots on pageseeder
    except KeyError:
        pageseeder_screens = []

    with open('src/review.json','r') as stream:
        no_ss = json.load(stream)['no_ss']
        for domain in no_ss:
            jpgName = f"{domain.replace('.','_')}.jpg"
            if jpgName not in pageseeder_screens:
                shutil.copyfile('src/placeholder.jpg', f'out/screenshots/{jpgName}')


@utils.handle
def sentenceStale():
    """
    Adds 30-day timer to files present on pageseeder but not locally
    """
    today = datetime.now().date()
    stale = set()
    # for every folder in context on pageseeder
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
                        expiry = date.fromisoformat(marked_stale['date'])
                        if expiry <= today:
                            ps_api.archive(uri)
                    else:
                        if labels:
                            labels += ','
                        else:
                            labels = ''
                        labels += f'expires-{today + timedelta(days = 30)}'
                        ps_api.patch_uri(uri, {'labels':labels})
                        stale.add(uri)
    if stale:
        with open('src/review.json', 'r') as stream:
            review = json.load(stream)
        with open('src/review.json', 'w') as stream:
            review['stale'] = list(stale)
            stream.write(json.dumps(review, indent=2))

            

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
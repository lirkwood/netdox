import json
import os
import shutil
import sys

from cryptography.fernet import Fernet
from netdox import utils
from pytest import fixture

global CRYPTO_KEY
CRYPTO_KEY = ''

global CONFIG
CONFIG = {
    'pageseeder': {
        'id': 'API_ID',
        'secret': 'API_SECRET',
        'username': 'USERNAME',
        'password': 'PASSWORD',
        'host': 'PS_FQDN',
        'group': 'PS_GROUP'
    },
    'plugins': {}
}

global ROLES
ROLES = {
    'exclusions':[
        'domainkey.com', 
        '_some_random_site.tld'
    ],
    'default': {
        'desc': 'Default role.',
        'uri': 999
    }}

global LOCATIONS
LOCATIONS = {
    'Subnet0': ['192.168.0.0/24'],
    'Subnet1or2': [
        '192.168.1.0/24',
        '192.168.2.0/24'
    ],
    'Internal': ['192.168.0.0/16'],
    'Any': ['0.0.0.0/0']
}

@fixture(scope = 'session', autouse = True)
def setupenv():
    """
    Sets up the environment to ensure no config files get overwritten.
    """
    # set dir to testdir
    startdir = os.getcwd()
    os.chdir(os.path.dirname(__file__))

    # backup files
    shutil.copytree(utils.APPDIR+ 'src/', 'srcbkp')

    cfg_location = None
    if os.path.exists(utils.APPDIR+ 'cfg'):
        cfg_location = os.readlink(utils.APPDIR+ 'cfg')
        os.remove(utils.APPDIR+ 'cfg')
    
    os.mkdir('tmpcfg')
    os.symlink(
        os.path.abspath('tmpcfg'), 
        utils.APPDIR+ 'cfg', 
        target_is_directory = True
    )

    # generate new crypto key
    global CRYPTO_KEY
    CRYPTO_KEY = Fernet.generate_key()
    with open(utils.APPDIR+ 'src/.crpt', 'wb') as stream:
        stream.write(CRYPTO_KEY)

    # copy fake files
    with open(utils.APPDIR+ 'src/config.bin', 'wb') as stream:
        stream.write(utils.Cryptor().encrypt(
            bytes(json.dumps(CONFIG), encoding = sys.getdefaultencoding())
        ))
        
    with open(utils.APPDIR+ 'cfg/roles.json', 'w') as stream:
        stream.write(json.dumps(ROLES))
        
    with open(utils.APPDIR+ 'cfg/locations.json', 'w') as stream:
        stream.write(json.dumps(LOCATIONS))

    #####
    yield
    #####

    shutil.rmtree(utils.APPDIR+ 'src')
    shutil.copytree('srcbkp', utils.APPDIR+ 'src')
    shutil.rmtree('srcbkp')
    
    shutil.rmtree('tmpcfg')
    os.remove(utils.APPDIR+ 'cfg')
    if cfg_location:
        os.symlink(
            os.path.abspath(cfg_location), 
            utils.APPDIR+ 'cfg', 
            target_is_directory = True
        )

    os.chdir(startdir)


@fixture
def hide_file():
    global _path
    _path = ''
    def hide(path: str):
        global _path
        _path = path
        os.rename(path, path + '.bkp')

    yield hide

    if _path and os.path.exists(_path + '.bkp'):
        os.rename(_path + '.bkp', _path)
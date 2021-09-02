import os
import sys
import shutil
import json

import pytest
from cryptography.fernet import Fernet
from netdox import utils

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
ROLES = {'exclusions':['domainkey.com', '_some_random_site.tld']}

@pytest.fixture(scope = 'module', autouse = True)
def setupenv(request):
    """
    Sets up the environment to ensure no config files get overwritten.
    """
    # set dir to testdir
    os.chdir(request.fspath.dirname)

    # backup files
    shutil.copytree(utils.APPDIR+ 'src/', 'srcbkp')

    os.mkdir('tmpcfg')
    cfg_location = os.readlink(utils.APPDIR+ 'cfg')
    os.remove(utils.APPDIR+ 'cfg')
    os.symlink(
        os.path.abspath('tmpcfg'), 
        utils.APPDIR+ 'cfg', 
        target_is_directory = True
    )

    global CRYPTO_KEY
    CRYPTO_KEY = Fernet.generate_key()
    with open(utils.APPDIR+ 'src/.crpt', 'wb') as stream:
        stream.write(CRYPTO_KEY)

    #####
    yield
    #####

    shutil.rmtree(utils.APPDIR+ 'src')
    shutil.copytree('srcbkp', utils.APPDIR+ 'src')

    os.remove(utils.APPDIR+ 'cfg')
    os.symlink(
        os.path.abspath(cfg_location), 
        utils.APPDIR+ 'cfg', 
        target_is_directory = True
    )

    shutil.rmtree('srcbkp')
    shutil.rmtree('tmpcfg')
    os.chdir(request.config.invocation_dir)


@pytest.fixture
def mock_cfg():
    """
    Encrypts *CONFIG* and writes to config location.
    """
    with open(utils.APPDIR+ 'src/config.bin', 'wb') as stream:
        stream.write(utils.Cryptor().encrypt(
            bytes(json.dumps(CONFIG), encoding = sys.getdefaultencoding())
        ))

def test_config(mock_cfg):
    """
    Tests the output of ``utils.config()``.
    """
    assert utils.config() == CONFIG


@pytest.fixture
def mock_roles():
    """
    Writes *ROLES* to roles location.
    """
    with open('tmpcfg/roles.json', 'w') as stream:
        stream.write(json.dumps(ROLES))

def test_roles(mock_roles):
    """
    Tests the output of ``utils.roles()``.
    """
    assert utils.roles() == ROLES
    os.remove('tmpcfg/roles.json')
    assert utils.roles() == utils.DEFAULT_DOMAIN_ROLES


def test_handle():
    """
    Tests the ``handle`` decorator.
    """
    assert utils.handle(lambda: 'return value')() == 'return value'
    assert utils.handle(lambda: 1 / 0)() == None
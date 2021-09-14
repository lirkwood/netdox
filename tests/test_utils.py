import json
import os
import shutil
from random import choices
from string import ascii_letters
from sys import getdefaultencoding
from bs4 import BeautifulSoup

import pytest
from conftest import CONFIG, ROLES
from netdox import utils, psml


def test_cryptor():
    if os.path.exists(utils.APPDIR+ 'src/.crpt'):
        shutil.move(utils.APPDIR+ 'src/.crpt', '.crpt.bkp')
    
    with pytest.raises(FileNotFoundError):
        utils.Cryptor()
    
    if os.path.exists('.crpt.bkp'):
        shutil.move('.crpt.bkp', utils.APPDIR+ 'src/.crpt')


@pytest.fixture
def mock_file() -> bytes:
    """
    Creates a file called ``message`` with random content.
    """
    message = ''.join(choices(ascii_letters, k = 99))
    with open('message', 'w') as stream:
        stream.write(message)

    yield message

    os.remove('message')

def test_encrypt_file(mock_file):
    utils.encrypt_file('message', 'ciphertext')
    with open('ciphertext', 'r') as stream:
        assert stream.read() != mock_file

    os.remove('ciphertext')


@pytest.fixture
def mock_encrypted_file() -> bytes:
    """
    Creates a file called ``ciphertext`` with random encrypted content.
    """
    message = ''.join(choices(ascii_letters, k = 99))
    with open('ciphertext', 'wb') as stream:
        stream.write(
            utils.Cryptor().encrypt(bytes(message, getdefaultencoding()))
        )

    yield message

    os.remove('ciphertext')

def test_decrypt_file(mock_encrypted_file):
    utils.decrypt_file('ciphertext', 'plaintext')

    with open('plaintext', 'r') as stream:
        assert stream.read() == mock_encrypted_file

    os.remove('plaintext')


def test_config():
    """
    Tests the output of ``utils.config()``.
    """
    assert utils.config() == CONFIG

    with pytest.raises(AttributeError):
        utils.config('fake plugin')

    shutil.move(utils.APPDIR+ 'src/config.bin', 'cfg.bkp')
    utils.config.cache_clear()
    with pytest.raises(FileNotFoundError):
        utils.config()
    shutil.move('cfg.bkp', utils.APPDIR+ 'src/config.bin')

def test_roles():
    """
    Tests the output of ``utils.roles()``.
    """
    assert utils.roles() == ROLES
    os.remove(utils.APPDIR+ 'cfg/roles.json')
    utils.roles.cache_clear()
    assert utils.roles() == utils.DEFAULT_DOMAIN_ROLES

def test_handle():
    """
    Tests the ``handle`` decorator.
    """
    assert utils.handle(lambda: 'return value')() == 'return value'
    assert utils.handle(lambda: 1 / 0)() == None


@pytest.fixture
def mock_dir():
    """
    Creates a mock directory structure to search.
    """
    for dir in [
        'mockdir',
        'mockdir/mock_subdir_1',
        'mockdir/mock_subdir_2',
        'mockdir/mock_subdir_2/mock_sub_subdir',
    ]:
        os.mkdir(dir)

    for file in [
        'mockdir/file.ext1',
        'mockdir/mock_subdir_1/file.ext1',
        'mockdir/mock_subdir_1/file.ext2',
        'mockdir/mock_subdir_2/file.ext1',
        'mockdir/mock_subdir_2/mock_sub_subdir/file.ext2'
    ]:
        open(file, 'w').close()
    
    yield

    shutil.rmtree('mockdir')

def test_fileFetchRecursive(mock_dir):
    """
    Tests the ``fileFetchRecursive`` function.
    """
    # relative to cwd
    assert utils.fileFetchRecursive('mockdir', '.') == [
        os.path.normpath(path) for path in [
        'mockdir/file.ext1',
        'mockdir/mock_subdir_1/file.ext1',
        'mockdir/mock_subdir_1/file.ext2',
        'mockdir/mock_subdir_2/file.ext1',
        'mockdir/mock_subdir_2/mock_sub_subdir/file.ext2'
    ]]

    # relative to APPDIR
    assert utils.fileFetchRecursive('mockdir') == [
        os.path.relpath(path, utils.APPDIR) for path in [
        'mockdir/file.ext1',
        'mockdir/mock_subdir_1/file.ext1',
        'mockdir/mock_subdir_1/file.ext2',
        'mockdir/mock_subdir_2/file.ext1',
        'mockdir/mock_subdir_2/mock_sub_subdir/file.ext2'
    ]]

    # restrict extension
    assert utils.fileFetchRecursive('mockdir', '.', 'ext1') == [
        os.path.normpath(path) for path in [
        'mockdir/file.ext1',
        'mockdir/mock_subdir_1/file.ext1',
        'mockdir/mock_subdir_2/file.ext1',
    ]]
    assert utils.fileFetchRecursive('mockdir', '.', 'ext2') == [
        os.path.normpath(path) for path in [
        'mockdir/mock_subdir_1/file.ext2',
        'mockdir/mock_subdir_2/mock_sub_subdir/file.ext2'
    ]]


def add_role(name: str, config: dict):
    """
    Adds a role to the roles config file.
    """
    utils.roles.cache_clear()
    roles = utils.roles()
    roles[name] = config
    with open(utils.APPDIR+ 'cfg/roles.json', 'w') as stream:
        stream.write(json.dumps(roles))
    utils.roles.cache_clear()

def test_roleToPSML():
    """
    Tests the ``roleToPSML`` function.
    """
    role_name = 'fake_role_name'
    add_role(role_name, {
        'property 1': 'value 1',
        'property 2': 'value 2',
        'property 3': 'value 3',
    })
    if not os.path.exists(utils.APPDIR+ 'out/config'):
        os.makedirs(utils.APPDIR+ 'out/config')
    utils.roleToPSML(role_name)

    with open(utils.APPDIR+ f'out/config/{role_name}.psml', 'r') as stream:
        roledoc = BeautifulSoup(stream.read(), 'lxml')
    
    assert roledoc.find(
        'properties-fragment', id = 'config'
    ) == psml.PropertiesFragment(
        id = 'config',
        properties = [
            psml.Property('name', 'Name', role_name),
            psml.Property('property 1', 'property 1', 'value 1'),
            psml.Property('property 2', 'property 2', 'value 2'),
            psml.Property('property 3', 'property 3', 'value 3'),
        ]
    )

    os.remove(utils.APPDIR+ f'out/config/{role_name}.psml')
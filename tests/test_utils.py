import json
import os
import shutil
from random import choices
from string import ascii_letters
from sys import getdefaultencoding
from bs4 import BeautifulSoup
from datetime import date, timedelta

import pytest
from conftest import CONFIG, hide_file
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


def test_config(hide_file):
    """
    Tests the output of ``utils.config()``.
    """
    assert utils.config() == CONFIG

    with pytest.raises(AttributeError):
        utils.config('fake plugin')

    hide_file(utils.APPDIR + 'src/config.bin')
    utils.config.cache_clear()
    with pytest.raises(FileNotFoundError):
        utils.config()

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

def test_path_list(mock_dir):
    """
    Tests the ``path_list`` function.
    """
    # relative to cwd
    assert set(utils.path_list('mockdir', '.')) == {
        os.path.normpath(path) for path in [
        'mockdir/file.ext1',
        'mockdir/mock_subdir_1/file.ext1',
        'mockdir/mock_subdir_1/file.ext2',
        'mockdir/mock_subdir_2/file.ext1',
        'mockdir/mock_subdir_2/mock_sub_subdir/file.ext2'
    ]}

    # relative to APPDIR
    assert set(utils.path_list('mockdir')) == {
        os.path.relpath(path, utils.APPDIR) for path in [
        'mockdir/file.ext1',
        'mockdir/mock_subdir_1/file.ext1',
        'mockdir/mock_subdir_1/file.ext2',
        'mockdir/mock_subdir_2/file.ext1',
        'mockdir/mock_subdir_2/mock_sub_subdir/file.ext2'
    ]}

def test_rootDomainExtract():
    assert utils.root_domain('domain.com.au') == 'domain.com.au'
    assert utils.root_domain('sub.domain.co.uk') == 'domain.co.uk'
    assert utils.root_domain('subsub.sub.domain.net') == 'domain.net'
    assert utils.root_domain('subsub.sub.domain.gov.au') == 'domain.gov.au'
    assert utils.root_domain('domain.faketld') == 'faketld'

def test_validatePSML_success():
    assert utils.validate_psml('<document level="portable" />')

def test_validatePSML_failure():
    assert not utils.validate_psml('<invalid-tag />')

def test_staleReport():
    today = date.today()
    plus_thirty = today + timedelta(days = 30)
    report = utils.stale_report({
        today: ['0', '1', '2'],
        plus_thirty: ['3', '4', '5']
    })

    assert utils.validate_psml(report)
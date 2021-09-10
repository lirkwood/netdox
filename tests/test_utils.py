import os
import shutil

import pytest
from conftest import CONFIG, ROLES
from netdox import utils


def test_config():
    """
    Tests the output of ``utils.config()``.
    """
    assert utils.config() == CONFIG

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

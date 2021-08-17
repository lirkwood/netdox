"""
This module contains any multi-purpose or generic code for use by both internal processes and plugins.
"""

from __future__ import annotations

import json
import os
import re
from functools import wraps
from sys import argv
from traceback import format_exc

from netdox.crypto import Cryptor

####################
# Global constants #
####################

global APPDIR
APPDIR = os.path.normpath(os.path.dirname(os.path.realpath(__file__))) + os.sep

global DEFAULT_CONFIG
DEFAULT_CONFIG = {
    'pageseeder': {
        'id': '',
        'secret': '',
        'username': '',
        'password': '',
        'host': '',
        'group': ''
    },
    'plugins': {}
}

def config() -> dict:
    """
    Loads the encrypted config file if it exists

    :return: A dictionary of configuration values.
    :rtype: dict
    """
    try:
        with open(APPDIR+ 'src/config.bin', 'rb') as stream:
            return json.loads(str(Cryptor().decrypt(stream.read()), encoding='utf-8'))
    except Exception:
        raise FileNotFoundError('Failed to find, decrypt, or read primary configuration file')


global DEFAULT_DOMAIN_ROLES
DEFAULT_DOMAIN_ROLES = {'exclusions': []}

def roles() -> dict:
    """
    Loads the domain roles file if it exists

    :return: A dictionary of configuration values.
    :rtype: dict
    """
    try:
        with open(APPDIR+ 'src/roles.json', 'r') as stream:
            return json.load(stream)
    except Exception:
        print('[WARNING][utils] Failed to find or read domain roles configuration file')
        return DEFAULT_DOMAIN_ROLES


dns_name_pattern = re.compile(r'([a-zA-Z0-9_-]+\.)+[a-zA-Z0-9_-]+')

##############
# Decorators #
##############

def handle(func):
    """
    Catches any exceptions raised by the passed function, prints the traceback, and returns *None*.
    Useful for functions which perform non-essential operations.
    """
    funcname = func.__name__
    funcmodule = func.__module__
    if funcmodule == '__main__':
        funcmodule = argv[0].replace('.py','')
        
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            returned = func(*args, **kwargs)
        except Exception:
            print(f'[WARNING][utils] Function {funcmodule}.{funcname} threw an exception:\n {format_exc()}')
            return None
        else:
            return returned
    return wrapper


#######################################
# Miscellaneous convenience functions #
#######################################

def fileFetchRecursive(dir: str, relative: str = APPDIR, extension: str = None) -> list[str]:
    """
    Returns a list of paths of all files descended from some directory. 
    By default paths are returned relative to *APPDIR*. 

    :param dir: The path to the directory to search for files in, relative to *relative*.
    :type dir: str
    :param relative: The path base path *dir* is relative to. Will not be included in returned paths.
    :param extension: The file extension to restrict your search to, defaults to None
    :type extension: str, optional
    :return: A list of paths to the files descended from *dir*.
    :rtype: list[str]
    """
    fileset = []
    for file in os.scandir(dir):
        if file.is_dir():
            fileset += fileFetchRecursive(file.path)
        elif file.is_file() and not (extension and not file.name.endswith(extension)):
            fileset.append(os.path.normpath(os.path.relpath(file.path, relative)))
    return fileset

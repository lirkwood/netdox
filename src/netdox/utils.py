"""
This module contains any multi-purpose or generic code for use by both internal processes and plugins.
"""

from __future__ import annotations

import json
import logging
import os
import re
from functools import cache, wraps
from sys import argv
from traceback import format_exc

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

################
# Cryptography #
################

class Cryptor(Fernet):
    """
    Can encrypt and decrypt files using the generated cryptography key.
    """
    def __init__(self):
        try:
            with open(APPDIR+ 'src/.crpt', 'rb') as stream:
                key = stream.read()
        except Exception:
            raise FileNotFoundError('Failed to locate cryptography key. Try \'netdox init\'.')
        else:
            super().__init__(key)

def encrypt_file(inpath: str, outpath: str = None) -> str:
    """
    Encrypts the file at *inpath* and saves the resulting fernet token to *outpath*.

    :param inpath: The file to encrypt.
    :type inpath: str
    :param outpath: The path to save the resulting token to, defaults to *inpath* + '.bin'.
    :type outpath: str, optional
    :return: The absolute path of the output file.
    :rtype: str
    """
    outpath = outpath or (inpath + '.bin')
    with open(inpath, 'rb') as instream, open(outpath, 'wb') as outstream:
        outstream.write(Cryptor().encrypt(instream.read()))
    return os.path.abspath(outpath)

def decrypt_file(inpath: str, outpath: str = None) -> str:
    """
    Decrypts the fernet token at *inpath* and saves the resulting content to *outpath*.

    :param inpath: The file to decrypt.
    :type inpath: str
    :param outpath: The path to save the resulting content to, defaults to *inpath* + '.txt'.
    :type outpath: str, optional
    :return: The absolute path of the output file.
    :rtype: str
    """
    outpath = outpath or (inpath + '.txt')
    with open(inpath, 'rb') as instream, open(outpath, 'wb') as outstream:
        outstream.write(Cryptor().decrypt(instream.read()))
    return os.path.abspath(outpath)

####################
# Global constants #
####################

global APPDIR
APPDIR = os.path.normpath(os.path.dirname(os.path.realpath(__file__))) + os.sep

@cache
def config(plugin: str = None) -> dict:
    """
    Loads the encrypted config file if it exists.

    :param plugin: The plugin to select the config of, defaults to None
    :type plugin: str, optional
    :raises FileNotFoundError: If the config file is not present of parseable.
    :return: A dictionary of configuration values.
    :rtype: dict
    """
    try:
        with open(APPDIR+ 'src/config.bin', 'rb') as stream:
            conf = json.loads(str(Cryptor().decrypt(stream.read()), encoding='utf-8'))
            return conf['plugins'][plugin] if plugin else conf
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
        with open(APPDIR+ 'cfg/roles.json', 'r') as stream:
            return json.load(stream)
    except Exception:
        logger.warning('Failed to find or read domain roles configuration file')
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
            logger.error(f'Function {funcmodule}.{funcname} threw an exception:\n {format_exc()}')
            return None
        else:
            return returned
    return wrapper


#######################################
# Miscellaneous convenience functions #
#######################################

def fileFetchRecursive(dir: str, relative: str = None, extension: str = None) -> list[str]:
    """
    Returns a list of paths of all files descended from some directory. 
    By default paths are returned relative to *APPDIR*. 

    :param dir: The path to the directory to search for files in.
    :type dir: str
    :param relative: The path all returned paths will be relative to.
    :type relative: str, optional
    :param extension: The file extension to restrict your search to, defaults to None
    :type extension: str, optional
    :return: A list of paths to the files descended from *dir*.
    :rtype: list[str]
    """
    relative = relative or APPDIR
    fileset = []
    for file in os.scandir(dir):
        if file.is_dir():
            fileset += fileFetchRecursive(file.path, relative, extension)
        elif file.is_file() and not (extension and not file.name.endswith(extension)):
            fileset.append(os.path.relpath(file.path, relative))
    return fileset

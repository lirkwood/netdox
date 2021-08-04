"""
This module contains any multi-purpose or generic code for use by both internal processes and plugins.
"""

from __future__ import annotations

import json
import re
from functools import wraps
from os import scandir
from sys import argv
from textwrap import dedent
from traceback import format_exc, print_exc

from crypto import Cryptor

####################
# Global constants #
####################

global DEFAULT_CONFIG, _config
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
        with open('src/config.bin', 'rb') as stream:
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
        with open('src/roles.json', 'r') as stream:
            return json.load(stream)
    except Exception:
        print('[WARNING][utils] Failed to find or read domain roles configuration file')
        return DEFAULT_DOMAIN_ROLES


MIN_STYLESHEET = '<xsl:stylesheet version="3.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" exclude-result-prefixes="#all" />'

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

def xslt(*_):
    print('[WARNING][utils] XSLT was called')


def jsonForXslt(xmlpath: str, jsonpath: str) -> None:
    """
    Generates an XML document that has a single element with name root containing the content of the JSON file.

    :param xmlpath: The path to output the import file to
    :type xmlpath: str
    :param jsonpath: The path, relative to the xmlpath, of the JSON file to import
    :type jsonpath: str
    """    
    with open(xmlpath, 'w') as stream:
        stream.write(dedent(f"""
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE import [
            <!ENTITY json SYSTEM "{jsonpath}">
            ]>
            <root>&json;</root>""").strip())


def fileFetchRecursive(dir: str, extension: str = None) -> list[str]:
    """
    Returns a list of paths of all files descended from some directory.

    :param dir: The path to the directory to search for files in.
    :type dir: str
    :param extension: The file extension to restrict your search to, defaults to None
    :type extension: str, optional
    :return: A list of paths to the files descended from *dir*.
    :rtype: list[str]
    """
    fileset = []
    for file in scandir(dir):
        if file.is_dir():
            fileset += fileFetchRecursive(file.path)
        elif file.is_file() and not (extension and not file.name.endswith(extension)):
            fileset.append(file.path)
    return fileset

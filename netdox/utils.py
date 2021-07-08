"""
This module contains any multi-purpose or generic code for use by both internal processes and plugins.

This script is mostly to improve the development process and encourage code reuse. 
It contains the two main classes used within Netdox, *DNSRecord* and *PTRRecord*, which represent all the DNS records which share a name.
It also defines two decorators which are used throughout Netdox, and some other functions which became useful across multiple scripts.
"""

from __future__ import annotations

import json
import subprocess
from functools import wraps
from os import DirEntry, scandir
from sys import argv
from textwrap import dedent
from traceback import format_exc
from typing import Union

#########################
# Global datastructures #
#########################

global DEFAULT_CONFIG, _cofig
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
_config = dict(DEFAULT_CONFIG)

def config():
    """
    Loads the config file as a global var if it exists
    """
    global _config
    try:
        with open('src/config.json', 'r') as stream:
            _config = json.load(stream)
    except FileNotFoundError:
        print('[WARNING][utils] Failed to load Netdox configuration file')
    return _config


global DEFAULT_ROLES, _roles
DEFAULT_ROLES = {'exclusions': []}
_roles = dict(DEFAULT_ROLES)

def roles():
    """
    Loads the DNS roles file as a global var if it exists
    """
    global _roles
    try:
        with open('src/roles.json', 'r') as stream:
            _roles = json.load(stream)
    except FileNotFoundError:
        print('[WARNING][utils] Failed to load DNS roles configuration file')
    return _roles

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

def xslt(xsl: str, src: str, out: bool = None):
    """
    Runs some xslt using Saxon
    """
    xsltpath = 'java -jar /usr/local/bin/saxon-he-10.3.jar'
    if out:
        subprocess.run(f'{xsltpath} -xsl:{xsl} -s:{src} -o:{out}', shell=True)
    else:
        subprocess.run(f'{xsltpath} -xsl:{xsl} -s:{src}', shell=True)


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


def fileFetchRecursive(dir: Union[str, DirEntry]) -> list[str]:
    """
    Returns a list of paths of all files descended from some directory.
    """
    if isinstance(dir, DirEntry):
        dir = dir.path
    elif not isinstance(dir, str):
        raise ValueError(f'Directory must be one of: str, os.DirEntry; Not {type(dir)}')
    
    fileset = []
    for file in scandir(dir):
        if file.is_dir():
            fileset += fileFetchRecursive(file)
        elif file.is_file():
            fileset.append(file.path)
    return fileset


####################
# Useful Constants #
####################

MIN_STYLESHEET = '<xsl:stylesheet version="3.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" exclude-result-prefixes="#all" />'
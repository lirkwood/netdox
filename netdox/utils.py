"""
This module contains any multi-purpose or generic code for use by both internal processes and plugins.

This script is mostly to improve the development process and encourage code reuse. 
It contains the two main classes used within Netdox, *DNSRecord* and *PTRRecord*, which represent all the DNS records which share a name.
It also defines two decorators which are used throughout Netdox, and some other functions which became useful across multiple scripts.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from functools import wraps
from os import DirEntry, scandir
from sys import argv
from traceback import format_exc
from typing import Union

##################
# Authentication #
##################

global authdict
authdict = {}

def auth():
    global authdict
    """
    Returns the contents of the main configuration file, ``authentication.json``.
    If the file has not yet been opened in this instance, it is opened and read first.

    :Returns:
        A dictionary containing the authentication/configuration details for PageSeeder and any plugins which use it.
    """
    if not authdict:
        with open('src/authentication.json', 'r') as stream:
            authdict = json.load(stream)
    return authdict


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


global config
config = {'exclusions': []}

def loadConfig():
    """
    Loads the DNS config as a global var if it exists
    """
    global config
    try:
        with open('src/config.json', 'r') as stream:
            config = json.load(stream)
    except FileNotFoundError:
        pass


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

"""
This module contains some utility functions / useful constants.
"""

from __future__ import annotations

import json
import logging
import os
import re
from functools import cache, wraps
from traceback import format_exc
from tldextract import extract
from datetime import date, timedelta
from bs4.element import Tag

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

#############
# Constants #
#############

APPDIR = os.path.normpath(os.path.dirname(os.path.realpath(__file__))) + os.sep
"""Absolute path to the directory containing the running source code."""

OUTDIRS = ('domains', 'ips', 'nodes')
"""Tuple of directories documents will be written to. 
Relative to the output directory / PageSeeder website context."""

## Regex patterns

dns_name_pattern = re.compile(r'([a-zA-Z0-9_-]+\.)+[a-zA-Z0-9_-]+')
expiry_date_pattern = re.compile(r'expires-(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})')
docid_invalid_patten = re.compile(r'[^a-zA-Z0-9_-]')

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

##################
# Config loaders #
##################

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
    except KeyError:
        raise AttributeError(f"Missing key 'plugins' or 'plugins.{plugin}' in primary config file.")
    except Exception:
        raise FileNotFoundError('Failed to find, decrypt, or read primary configuration file')


##############
# Decorators #
##############

def handle(func):
    """
    Catches any exceptions raised by the passed function, prints the traceback, and returns *None*.
    Useful for functions which perform non-essential operations.
    """ 
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            returned = func(*args, **kwargs)
        except Exception:
            logger.error(f'Function {func.__module__}.{func.__name__} threw an exception:\n {format_exc()}')
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

def rootDomainExtract(fqdn: str) -> str:
    """
    Returns the root domain and TLD suffix of a FQDN.
    e.g. for subsub.sub.domain.com.au, would return domain.com.au

    :param fqdn: The full qualified domain name to extract the root domain from.
    :type fqdn: str
    :return: The root domain and TLD suffix.
    :rtype: str
    """
    result = extract(fqdn)
    return result.domain +'.'+ result.suffix

def staleReport(stale: dict[date, list[str]]) -> str:
    """
    Returns a section describing stale network objects for the report.

    :param stale: A dict mapping date to a list of URIs that expire on that day.
    :type stale: dict[date, list[str]]
    :return: A PSML section tag with an id of 'stale'.
    :rtype: str
    """
    section = Tag(is_xml = True, 
        name = 'section', 
        attrs = {
            'id': 'stale', 
            'title': 'Stale Documents'
    })

    plus_thirty = date.today() + timedelta(days = 30)

    if plus_thirty in stale:
        todayFrag = Tag(is_xml = True, name = 'fragment', attrs = {'id': plus_thirty.isoformat()})
        heading = Tag(is_xml = True, name = 'heading', attrs = {'level': '2'})
        heading.string = 'Sentenced Today'
        todayFrag.append(heading)

        for uri in stale.pop(plus_thirty):
            todayFrag.append(Tag(is_xml = True,
                name = 'blockxref',
                attrs = {
                    'frag': 'default',
                    'uriid': uri
                }
            ))
        section.insert(0, todayFrag)

    for expiry, uris in sorted(stale.items(), reverse = True):
        frag = Tag(is_xml = True, name = 'fragment', attrs = {'id': expiry.isoformat()})
        heading = Tag(is_xml=True, name='heading', attrs={'level': '2'})
        heading.string = 'Expiring on: '+ expiry.isoformat()
        frag.append(heading)
        for uri in uris:
            frag.append(Tag(is_xml = True,
                name = 'blockxref',
                attrs = {
                    'frag': 'default',
                    'uriid': uri
                }
            ))
        section.append(frag)
    return str(section)
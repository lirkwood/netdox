"""
Contains the logic for the command-line interface.
"""
import argparse
import logging
import os
import pathlib
import shutil
import sys
from datetime import date
from distutils.util import strtobool

from cryptography.fernet import Fernet

from netdox import pageseeder, config as _config_mod
from netdox.utils import APPDIR, CFGPATH, decrypt_file, encrypt_file, path_list
from netdox.utils import config as _config_file
from netdox import Network
from netdox.app import PluginManager, PluginWhitelist, App

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('[{asctime}] [{levelname:8}] {name} :: {message}', style = '{')

streamHandler = logging.StreamHandler(sys.stdout)
streamHandler.setLevel(logging.INFO)
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)

logging.getLogger('charset_normalizer').setLevel(logging.WARNING)

## Misc

def _confirm(message: str, default = False) -> bool:
    """
    Prompts the user to confirm *message* and returns the boolean representation of their answer.

    :param message: The message to display to the user.
    :type message: str
    :param default: The default value to take if the user simply presses return, defaults to False
    :type default: bool, optional
    :return: The user's answer
    :rtype: bool
    """
    resp = input(message)
    if not resp:
        return default
    else:
        return bool(strtobool(resp.lower().strip()))

## Init

def init_dirs():
    for path in ('src', 'out', 'logs'):
        if not os.path.exists(APPDIR+ path):
            os.mkdir(APPDIR+ path)

    with open(APPDIR+ 'src/.crpt', 'wb') as stream:
        stream.write(Fernet.generate_key())
    
    if os.path.exists(CFGPATH):
        os.remove(CFGPATH)

    if os.path.lexists(APPDIR+ 'cfg'):
        os.remove(APPDIR+ 'cfg')

def _copy_defaults(nwman: PluginManager):
    """
    Copies default config files / templates to dir at *path*.

    :params nwman: PluginManager object to use to generate app config template.
    :type nwman: PluginManager
    """
    for default_file in os.scandir(APPDIR+ 'src/defaults'):
        file_dest = os.path.realpath(
            os.path.join(APPDIR, 'cfg/', default_file.name))
        if default_file.name == 'config.json':
            if not _load_config(file_dest):
                _config_mod.gen_config_template(nwman)
                logger.info('No application config detected. ' +
                    f'Please populate the template at {file_dest}')
        else:
            if not os.path.exists(file_dest):
                shutil.copy(default_file.path, file_dest)

def _copy_readmes(nwman: PluginManager) -> int:
    """
    Discovers README files from the plugins in *nwman* 
    and copies them to a folder in the config directory.

    :param nwman: The PluginManager to read plugin data from.
    :type nwman: PluginManager
    :return: The number of README files successfully copied.
    :rtype: int
    """
    dest = os.path.join(APPDIR, 'cfg', 'README')
    if not os.path.exists(dest):
        os.mkdir(dest)

    copied = 0
    for plugin in nwman.plugins:
        plugin_path = plugin.module.__file__
        if plugin_path:
            if not os.path.isdir(plugin_path):
                plugin_path = os.path.dirname(plugin_path)
            for path in path_list(plugin_path):
                filename = os.path.basename(path).lower()
                if 'readme' in filename:
                    shutil.copyfile(APPDIR+ path, 
                        os.path.join(dest, f'{plugin.name}_{filename}'))
    return copied


def init(args: argparse.Namespace):
    """
    Initialises a new config directory and generates a new cryptography key.

    :param args: CLI args
    :type args: argparse.Namespace
    """
    if ((not os.path.exists(APPDIR+ 'src/config.bin')) or
    _confirm('This action will destroy the existing cryptography key, and your current configuration will be lost. Continue? [y/n] ')):

        # deactivate logging while initialising a networkmanager
        nwman_logger = logging.getLogger('netdox.nwman')
        nwman_level = nwman_logger.level
        nwman_logger.setLevel(logging.ERROR)
        nwman = PluginManager(whitelist = PluginWhitelist.WILDCARD)
        nwman_logger.setLevel(nwman_level)

        init_dirs()
        os.symlink(os.path.abspath(args.path), APPDIR+ 'cfg', 
            target_is_directory = True)
        _copy_defaults(nwman) 

        logger.debug(f'Copied {_copy_readmes(nwman)} plugin README files')
        logger.info('Initialisation of directory successful.')
    
    else: exit(0)

## Config

def _load_config(path: str) -> bool:
    """
    
    Loads the config file at *path* as the new app config.

    :param path: Path to the new config file.
    :type path: str
    :return: Returns True if config file successfully loaded. False otherwise.
    :rtype: bool
    """
    backup = APPDIR+ 'src/config.old'
    if os.path.exists(path):
        if os.path.exists(CFGPATH):
            shutil.copyfile(CFGPATH, backup)
        encrypt_file(path, CFGPATH)
        try:
            assert pageseeder.get_group()
        except Exception:
            logger.error(
                'Unable to contact or authenticate with the configured PageSeeder instance. '+ 
                'Please check your configuration and try again.')
            return False
        else:
            os.remove(path)
            if os.path.exists(backup):
                os.remove(backup)
            logger.info('Success: configuration is valid.')
            return True
    else:
        logger.error(f'Unable to find or parse config file at: {path}.')
        if os.path.exists(CFGPATH):
            os.remove(CFGPATH)
        if os.path.exists(backup):
            logger.info('Reverting to previous config.')
            shutil.move(backup, CFGPATH)
        return False

def config(args: argparse.Namespace):
    """
    Load a new config file or dump the current one.

    :param args: CLI args
    :type args: argparse.Namespace
    """
    if args.action == 'load':
        if ((not os.path.exists(CFGPATH)) or
        _confirm('This action will destroy your existing configuration if successful. Continue? [y/n] ')):
            if not _load_config(args.path):
                exit(1)
        exit(0)
    else:
        decrypt_file(CFGPATH, args.path)

## Refresh

def refresh(args: argparse.Namespace):
    """
    Generates a new set of documentation and uploads it to PageSeeder.
    """
    assert _config_file(), 'Config file is empty'
    debugHandler = logging.FileHandler(APPDIR+ f'logs/{date.today().isoformat()}.log')
    debugHandler.setLevel(logging.DEBUG)
    debugHandler.setFormatter(formatter)

    warningPath = APPDIR + 'src/warnings.log'
    if os.path.exists(warningPath): os.remove(warningPath)
    warningHandler = logging.FileHandler(warningPath)
    warningHandler.setLevel(logging.WARNING)
    warningHandler.setFormatter(formatter)

    logger.addHandler(debugHandler)
    logger.addHandler(warningHandler)
    logger.debug('Refresh begins')
    App().refresh(dry = args.dry_run)

## Crypto

def encrypt(args: argparse.Namespace):
    """
    Encrypts a file.

    :param args: CLI args
    :type args: argparse.Namespace
    """
    encrypt_file(str(args.inpath), str(args.outpath) if args.outpath else None)

def decrypt(args: argparse.Namespace):
    """
    Decrypts a file.

    :param args: CLI args
    :type args: argparse.Namespace
    """
    decrypt_file(str(args.inpath), str(args.outpath) if args.outpath else None)

## Parsing

def parse_args():
    parser = argparse.ArgumentParser(prog = 'netdox', description = 'Network documentation generator for use with PageSeeder.')
    subparsers = parser.add_subparsers(
        title = 'methods', 
        help = f'Try running \'{parser.prog} <method> -h\' for more detail',
        metavar = '<method> [args...]',
        dest = 'method'
    )
    parser.add_argument('-d', '--debug', action = 'store_true', help = 'Log DEBUG level messages to stdout.')

    init_parser = subparsers.add_parser('init', help = 'Initialises a new config directory and generates a new cryptography key.')
    init_parser.set_defaults(func = init)
    init_parser.add_argument('path', type = pathlib.Path, help = 'path to directory to initialise as the config directory.')

    config_parser = subparsers.add_parser('config', help = 'Load a new config file or dump the current one.')
    config_parser.add_argument('action', 
        choices = ['load', 'dump'], 
        metavar = '(load | dump)',
        help = 'action to perform on the config file'
    )
    config_parser.add_argument('path', type = pathlib.Path, help = 'path to read/write the config file from/to')
    config_parser.set_defaults(func = config)

    refresh_parser = subparsers.add_parser('refresh', help = 'Generates a new set of documentation and uploads it to PageSeeder.')
    refresh_parser.set_defaults(func = refresh)
    refresh_parser.add_argument('-d', '--dry-run', action = 'store_true', help = 'do not upload documents at the end of the refresh')

    encrypt_parser = subparsers.add_parser('encrypt', help = 'Encrypts a file.')
    encrypt_parser.add_argument('inpath', type = pathlib.Path, help = 'path to a file to encrypt.')
    encrypt_parser.add_argument('-o', '--outpath', type = pathlib.Path, help = 'path to save the encrypted file to. Default is {inpath}.bin')
    encrypt_parser.set_defaults(func = encrypt)

    decrypt_parser = subparsers.add_parser('decrypt', help = 'Decrypts a file.')
    decrypt_parser.add_argument('inpath', type = pathlib.Path, help = 'path to a file to decrypt.')
    decrypt_parser.add_argument('-o', '--outpath', type = pathlib.Path, help = 'path to save the decrypted file to. Default is {inpath}.txt')
    decrypt_parser.set_defaults(func = decrypt)


    args = parser.parse_args()
    if args.debug:
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)

    args.func(args)

if __name__ == '__main__':
    parse_args()

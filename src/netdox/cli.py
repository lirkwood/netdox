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
from netdox.refresh import main as _refresh
from netdox.utils import APPDIR, CFGPATH, decrypt_file, encrypt_file, fileFetchRecursive
from netdox.utils import config as _config_file
from netdox import Network, NetworkManager
from netdox.nwman import PluginWhitelist

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
        return strtobool(resp.lower().strip())

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

def _try_load_config(path: str) -> bool:
    """
    Tries to load config file at *path*. 

    :param path: Path to the new config file.
    :type path: str
    :return: True if the file was loaded successfully. False otherwise.
    :rtype: bool
    """
    if os.path.exists(APPDIR+ 'cfg/config.json'):
        logger.info('Config file already exists in target directory.')
        try:
            _load_config(path)
        except Exception:
            logger.error(f'Failed to load config file in target directory.')
            return False
        else:
            return True
    else:
        return False

def _copy_defaults(nwman: NetworkManager):
    """
    Copies default config files / templates to dir at *path*.

    :params nwman: NetworkManager object to use to generate app config template.
    :type nwman: NetworkManager
    """
    for default_file in os.scandir(APPDIR+ 'src/defaults'):
        file_dest = APPDIR+ 'cfg/'+ default_file.name
        if default_file.name == 'config.json':
            if not _try_load_config(file_dest):
                _config_mod.gen_config_template(nwman)
                logger.info('No application config detected. ' +
                    f'Please populate the template at {file_dest}')
        else:
            if not os.path.exists(file_dest):
                shutil.copy(default_file.path, file_dest)

def _copy_readmes(nwman: NetworkManager) -> int:
    """
    Discovers README files from the plugins in *nwman* 
    and copies them to a folder in the config directory.

    :param nwman: The NetworkManager to read plugin data from.
    :type nwman: NetworkManager
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
            for path in fileFetchRecursive(plugin_path):
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
        nwman = NetworkManager(whitelist = PluginWhitelist.WILDCARD, 
            network = Network())
        nwman_logger.setLevel(nwman_level)

        init_dirs()
        os.symlink(os.path.abspath(args.path), APPDIR+ 'cfg', 
            target_is_directory = True)
        _copy_defaults(nwman) 

        logger.debug(f'Copied {_copy_readmes(nwman)} plugin README files')
        logger.info('Initialisation of directory successful.')
    
    else: exit(0)

## Config

def _load_config(path: str) -> None:
    """
    Loads the config file at *path* as the new app config.

    :param path: Path to the new config file.
    :type path: str
    :raises ConnectionError: If the config file cannot be used to connect to PS.
    """
    backup = APPDIR+ 'src/config.old'
    if os.path.exists(CFGPATH):
        shutil.copyfile(CFGPATH, backup)
    if os.path.exists(path):
        encrypt_file(path, CFGPATH)
        try:
            assert pageseeder.get_group()
        except Exception:
            raise ConnectionError(
                'Unable to contact or authenticate with the configured PageSeeder instance. '+ 
                'Please check your configuration and try again.')
        else:
            os.remove(path)
            if os.path.exists(backup):
                os.remove(backup)
            logger.info('Success: configuration is valid.')
    else:
        logger.error(f'Unable to find or parse config file at: {path}. Reverting to previous config.')
        os.remove(CFGPATH)
        if os.path.exists(backup):
            shutil.move(backup, CFGPATH)

def config(args: argparse.Namespace):
    """
    Load a new config file or dump the current one.

    :param args: CLI args
    :type args: argparse.Namespace
    """
    if args.action == 'load':
        if ((not os.path.exists(CFGPATH)) or
        _confirm('This action will destroy your existing configuration if successful. Continue? [y/n] ')):
            _load_config(args.path)
        else: exit(0)
    else:
        decrypt_file(CFGPATH, args.path)

## Serve

def serve(_):
    """
    Begins serving the web server to listen for webhooks from PageSeeder.
    """
    raise NotImplementedError('Webhooks are not currently usable')

## Refresh

def refresh(args: argparse.Namespace):
    """
    Generates a new set of documentation and uploads it to PageSeeder.
    """
    assert _config_file(), 'Config file is empty'
    fileHandler = logging.FileHandler(APPDIR+ f'/logs/{date.today().isoformat()}.log')
    fileHandler.setLevel(logging.DEBUG)
    fileHandler.setFormatter(formatter)
    logger.addHandler(fileHandler)

    logger.debug('Refresh begins')

    _refresh(dry = args.dry_run)

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

    serve_parser = subparsers.add_parser('serve', help = 'Begins serving the web server to listen for webhooks from PageSeeder.')
    serve_parser.set_defaults(func = serve)

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

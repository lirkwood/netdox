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
import json
from collections import defaultdict
from typing import Union

from cryptography.fernet import Fernet

from netdox import pageseeder
from netdox.refresh import main as _refresh
from netdox.utils import APPDIR, decrypt_file, encrypt_file
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


def init_dirs():
    for path in ('src', 'out', 'logs'):
        if not os.path.exists(APPDIR+ path):
            os.mkdir(APPDIR+ path)

    with open(APPDIR+ 'src/.crpt', 'wb') as stream:
        stream.write(Fernet.generate_key())
    
    if os.path.exists(APPDIR+ 'src/config.bin'):
        os.remove(APPDIR+ 'src/config.bin')

    if os.path.lexists(APPDIR+ 'cfg'):
        os.remove(APPDIR+ 'cfg')

def _gen_config():
    with open(APPDIR+ 'src/defaults/config.json', 'r') as stream:
        app_config = json.load(stream)
    app_config['plugins'] = defaultdict(dict)

    # deactivate logging while initialising a networkmanager
    nwman_logger = logging.getLogger('netdox.nwman')
    nwman_level = nwman_logger.level
    nwman_logger.setLevel(logging.CRITICAL)

    # generate config template from plugins
    for plugin in NetworkManager(
        whitelist = PluginWhitelist.WILDCARD, 
        network = Network()
    ).plugins:
        plugin_name = plugin.__name__.split('.')[-1]
        plugin_config_model = getattr(plugin, '__config__', {})
        if plugin_config_model:
            try:
                json.dumps(plugin_config_model)
            except Exception:
                logger.error(
                    f"Plugin {plugin.__name__.split('.')[-1]} "
                    'registered an invalid JSON object under __config__.')
            else:
                app_config['plugins'][plugin_name] = plugin_config_model

    nwman_logger.setLevel(nwman_level)
    
    with open(APPDIR+ 'cfg/config.json', 'w') as stream:
        stream.write(json.dumps(app_config, indent = 2))

def _load_config():
    if os.path.exists(APPDIR+ 'cfg/config.json'):
        print('Config file already exists in target directory.')
        try:
            config_args = argparse.Namespace(
                action = 'load', path = APPDIR+ 'cfg/config.json')
            config(config_args)
        except Exception:
            print(f'Failed to load config file in target directory.')
            return False
        else:
            return True
    else:
        return False

def init(args: argparse.Namespace):
    """
    Initialises a new config directory and generates a new cryptography key.

    :param args: CLI args
    :type args: argparse.Namespace
    """
    if ((not os.path.exists(APPDIR+ 'src/config.bin')) or
    _confirm('This action will destroy the existing cryptography key, and your current configuration will be lost. Continue? [y/n] ')):

        init_dir = os.path.abspath(args.path)
        init_dirs()
        os.symlink(init_dir, APPDIR+ 'cfg', target_is_directory = True)
        config_loaded = False
        for default_file in os.scandir(APPDIR+ 'src/defaults'):
            if default_file.name == 'config.json':
                config_loaded = _load_config()
                if not config_loaded:
                    _gen_config()
            else:
                if not os.path.exists(APPDIR+ 'cfg/'+ default_file.name):
                    shutil.copy(default_file.path, APPDIR+ 'cfg/'+ default_file.name)
            
        print('Initialisation of directory successful.',
            'Please provide a config using \'netdox config\'.' if not config_loaded else '')
    
    else: exit(0)

def config(args: argparse.Namespace):
    """
    Load a new config file or dump the current one.

    :param args: CLI args
    :type args: argparse.Namespace
    """
    if args.action == 'load':
        if ((not os.path.exists(APPDIR+ 'src/config.bin')) or
        _confirm('This action will destroy your existing configuration if successful. Continue? [y/n] ')):
            if os.path.exists(APPDIR+ 'src/config.bin'):
                shutil.copyfile(APPDIR+ 'src/config.bin', APPDIR+ 'src/config.old')
            if os.path.exists(args.path):
                encrypt_file(args.path, APPDIR+ 'src/config.bin')
                try:
                    assert pageseeder.get_group()
                except Exception:
                    raise ConnectionError(
                        'Unable to contact or authenticate with the configured PageSeeder instance. '+ 
                        'Please check your configuration and try again.')
                else:
                    os.remove(args.path)
                    if os.path.exists(APPDIR+ 'src/config.old'):
                        os.remove(APPDIR+ 'src/config.old')
                    print('Success: configuration is valid.')
            else:
                logger.error(f'Unable to find or parse config file at: {args.path}. Reverting to previous config.')
                os.remove(APPDIR+ 'src/config.bin')
                if os.path.exists(APPDIR+ 'src/config.old'):
                    shutil.move(APPDIR+ 'src/config.old', APPDIR+ 'src/config.bin')

        else: exit(0)
    
    else:
        decrypt_file(APPDIR+ 'src/config.bin', args.path)

def serve(_):
    """
    Begins serving the web server to listen for webhooks from PageSeeder.
    """
    raise NotImplementedError('Webhooks are not currently usable')

def refresh(_):
    """
    Generates a new set of documentation and uploads it to PageSeeder.
    """
    assert _config_file(), 'Config file is empty'
    fileHandler = logging.FileHandler(APPDIR+ f'/logs/{date.today().isoformat()}.log')
    fileHandler.setLevel(logging.DEBUG)
    fileHandler.setFormatter(formatter)
    logger.addHandler(fileHandler)

    logger.debug('Refresh begins')

    _refresh()

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

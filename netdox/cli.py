import argparse
import os
import pathlib
import shutil

from cryptography.fernet import Fernet
from distutils.util import strtobool

from netdox import pageseeder
from netdox.refresh import main as _refresh
from netdox.utils import APPDIR, encrypt_file, decrypt_file

def _confirm(message: str, default = False):
    resp = input(message)
    if not resp:
        return default
    else:
        return strtobool(resp.lower().strip())


def init(args: argparse.Namespace):
    if not os.path.exists(APPDIR+ 'src/config.bin') or \
    _confirm('This action will destroy the existing cryptography key, and your current configuration will be lost. Continue? [y/n] '):
        # setting up dirs
        for path in ('src', 'out', 'logs'):
            if not os.path.exists(APPDIR+ path):
                os.mkdir(APPDIR+ path)
                
        for path in ('domains', 'ips', 'nodes', 'config'):
            if not os.path.exists(APPDIR+ 'out/'+ path):
                os.mkdir(APPDIR+ 'out/'+ path)

        with open(APPDIR+ 'src/.crpt', 'wb') as stream:
            stream.write(Fernet.generate_key())
        
        if os.path.exists(APPDIR+ 'src/config.bin'):
            os.remove(APPDIR+ 'src/config.bin')

        if os.path.exists(APPDIR+ 'cfg'):
            os.remove(APPDIR+ 'cfg')
        os.symlink(os.path.abspath(args.path), APPDIR+ 'cfg', target_is_directory = True)
        
        for file in os.scandir(APPDIR+ 'src/defaults/localconf'):
            shutil.copy(file.path, APPDIR+ 'cfg/'+ file.name)
            
        print('[INFO][netdox] Initialisation of directory successful. Please provide a config using \'netdox config\'.')
    
    else: exit(0)

def config(args: argparse.Namespace):
    if args.action == 'load':
        if _confirm('This action will destroy your existing configuration if successful. Continue? [y/n] '):
            if os.path.exists(APPDIR+ 'src/config.bin'):
                shutil.copyfile(APPDIR+ 'src/config.bin', APPDIR+ 'src/config.old')
            if os.path.exists(args.path):
                encrypt_file(args.path, APPDIR+ 'src/config.bin')
                try:
                    pageseeder.get_group()
                except Exception:
                    print('[ERROR][netdox] Unable to contact or authenticate with the configured PageSeeder instance. Please check your configuration and try again.')
                else:
                    os.remove(args.path)
                    if os.path.exists(APPDIR+ 'src/config.old'):
                        os.remove(APPDIR+ 'src/config.old')
                    print('[INFO][netdox] Success: configuration is valid.')
            else:
                print(f'[ERROR][netdox] Unable to find or parse config file at: {args.path}. Reverting to previous config.')
                os.remove(APPDIR+ 'src/config.bin')
                if os.path.exists(APPDIR+ 'src/config.old'):
                    shutil.move(APPDIR+ 'src/config.old', APPDIR+ 'src/config.bin')

        else: exit(0)
    
    else:
        decrypt_file(APPDIR+ 'src/config.bin', args.path)

def serve(_):
    raise NotImplementedError('Webhooks are not currently usable')

def refresh(_):
    _refresh()

def encrypt(args: argparse.Namespace):
    encrypt_file(str(args.inpath), str(args.outpath) if args.outpath else None)

def decrypt(args: argparse.Namespace):
    decrypt_file(str(args.inpath), str(args.outpath) if args.outpath else None)


def parse_args():
    parser = argparse.ArgumentParser(prog = 'netdox', description = 'Network documentation generator for use with PageSeeder.')
    subparsers = parser.add_subparsers(
        title = 'methods', 
        help = f'Try running \'{parser.prog} <method> -h\' for more detail',
        metavar = '<method> [args...]',
        dest = 'method'
    )

    init_parser = subparsers.add_parser('init', help = 'Initialises the working directory and generates a new cryptography key.')
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
    args.func(args)

if __name__ == '__main__':
    parse_args()
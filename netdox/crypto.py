"""
Cryptography module used by netdox to encrypt / decrypt sensitive files.
This script can be called like an executable, with the following signature:
`python crypto.py <encrypt|decrypt> <inpath> <outpath>`.
"""

import os
import sys

from cryptography.fernet import Fernet
from netdox import utils

class Cryptor(Fernet):
    def __init__(self):
        try:
            with open(utils.APPDIR+ 'src/crypto', 'rb') as stream:
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
    outpath = outpath or inpath + '.bin'
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
    outpath = outpath or inpath + '.txt'
    with open(inpath, 'rb') as instream, open(outpath, 'wb') as outstream:
        outstream.write(Cryptor().decrypt(instream.read()))
    return os.path.abspath(outpath)


if __name__ == '__main__':
    inpath = sys.argv[2]
    outpath = sys.argv[3] if len(sys.argv) > 3 else None

    if sys.argv[1] == 'encrypt':
        encrypt_file(inpath, outpath)

    elif sys.argv[1] == 'decrypt':
        decrypt_file(inpath, outpath)
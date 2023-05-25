from netdox import cli
from argparse import Namespace
import logging
logging.getLogger(__name__).setLevel(logging.DEBUG)
ns = Namespace()
ns.dry_run = True
try:
    cli.refresh(ns)
except KeyboardInterrupt:
    print('Exiting gracefully...')
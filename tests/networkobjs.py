import unittest
import sys, os
sys.path.append(os.path.abspath('..'))

from netdox import objs

class Testobjs(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        network = objs.Network()
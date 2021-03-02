import unittest, os

import iptools
class iptools_tests(unittest.TestCase):

    def test_letters(self):
        self.assertEqual(False, iptools.parsed_ip('abc.efg.hij.klm').valid)
        self.assertEqual(False, iptools.parsed_ip('192.168.0.abc').valid)
        self.assertEqual(False, iptools.parsed_ip('192.168.0.1a').valid)
    
    def test_octets(self):
        self.assertEqual(False, iptools.parsed_ip('192.168.0').valid)
        self.assertEqual(False, iptools.parsed_ip('192.168.0.').valid)
        self.assertEqual(False, iptools.parsed_ip('192.168.0.1.0').valid)
        self.assertEqual(False, iptools.parsed_ip('192.168.0.1.').valid)
        self.assertEqual(False, iptools.parsed_ip('.192.168.0.1').valid)
        self.assertEqual(True, iptools.parsed_ip('192.168.0.1').valid)

        self.assertIsInstance(iptools.parsed_ip('192.168.0.1').octets, list)
        self.assertEqual(['192','168','0','1'], iptools.parsed_ip('192.168.0.1').octets)


import ad_domains
class ad_domains_tests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.mkdir('testdir')

    @classmethod
    def tearDownClass(cls):
        for file in os.scandir('testdir'):
            os.remove(file)
        os.rmdir('testdir')

    def test_badpath(self):
        with self.assertRaises(FileNotFoundError):
            ad_domains.extract('foo')
    
    def test_nodata(self):
        self.assertEqual({'forward':{},'reverse':{}}, ad_domains.extract('testdir'))


import dnsme_domains
class dnsme_domains_tests(unittest.TestCase):
    
    def test_noauth(self):
        with open('src/authentication.json','r') as stream:
            authinf = stream.read()
        open('src/authentication.json','w').close()

        self.assertEqual({'forward':{},'reverse':{}}, dnsme_domains.main())

        with open('src/authentication.json','w') as stream:
            stream.write(authinf)

        

if __name__ == '__main__':
    unittest.main()
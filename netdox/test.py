import unittest, shutil, json, os

import utils

class utils_tests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        os.rename('src', 'tmp')
        os.mkdir('src')
        locations = {
            'Location 1': [
                '192.168.5.0/25',
                '192.168.5.128/25'
            ],
            'Location 2': [
                "192.168.6.0/24",
                "192.168.7.0/24",
                "192.168.8.0/24",
                "192.168.9.0/24",
                "192.168.10.0/24"
            ],
            'Location 3': [
                '192.168.1.0/24',
                '192.168.2.255/24',
                '192.168.3.99/24'
            ],
            'Location 4': [
                '192.168.128.0/17',
            ],
            'Location 5': [
                '192.168.0.0/16'
            ]
        }
        with open('src/locations.json', 'w') as stream:
            stream.write(json.dumps(locations))

    def test_func_locate(self):
        utils.loadLocations()

        self.assertEqual('Location 1', utils.locate('192.168.5.0'))
        self.assertEqual('Location 2', utils.locate('192.168.10.255'))
        self.assertEqual('Location 3', utils.locate('192.168.2.5'))
        self.assertEqual('Location 4', utils.locate('192.168.200.0'))
        self.assertEqual('Location 5', utils.locate('192.168.0.0'))

        self.assertEqual('Location 1', utils.locate([
            '192.168.5.1',
            '192.168.6.1'
        ]))
        self.assertEqual('Location 5', utils.locate([
            '192.168.0.0',
            '10.0.0.0',
            '255.9.9.255'
        ]))
        self.assertEqual('Location 4', utils.locate([
            '192.168.255.0',
            '192.168.0.0'
        ]))
        self.assertEqual(None, utils.locate([
            '192.168.1.0',
            '192.168.6.0',
            '192.168.7.0'
        ]))

        self.assertRaises(ValueError, utils.locate, '192.168.0.')
        self.assertRaises(ValueError, utils.locate, '192.168.0.256')
        self.assertRaises(ValueError, utils.locate, ['192.168.0.0', '192.168.0.1.2'])
        self.assertRaises(TypeError, utils.locate, 3232235521)

    def test_func_merge_records(self):
        record_1 = utils.DNSRecord('test.domain.com')
        record_1.link('other1.domain.com', type = 'cname', source = 'SomePlugin')
        record_1.link('other2.domain.com', type = 'cname', source = 'SomePlugin')
        record_1.link('192.168.0.1', type = 'ipv4', source = 'SomePlugin')
        record_1.link('SomeResourceID', type = 'SomeResourcePlugin')

        record_2 = utils.DNSRecord('test.domain.com', root = 'domain.com')
        record_2.link('other1.domain.com', type = 'cname', source = 'SomePlugin')
        record_2.link('other2.domain.com', type = 'cname', source = 'OtherPlugin')
        record_2.link('192.168.0.2', type = 'ipv4', source = 'SomePlugin')
        record_2.link('200.0.0.2', type = 'ip', source = 'SomePlugin')
        record_2.link('OtherResourceID', type = 'SomeResourcePlugin')
        record_2.link('OtherResourceID', type = 'OtherResourcePlugin')

        union = utils.merge_records(record_1, record_2)

        self.assertCountEqual({
            ('other1.domain.com', 'SomePlugin'),
            ('other2.domain.com', 'SomePlugin'),
            ('other2.domain.com', 'OtherPlugin')
        }, union._cnames)
        self.assertCountEqual([
            'other1.domain.com',
            'other2.domain.com'
        ], union.cnames)

        self.assertCountEqual({
            ('192.168.0.1', 'SomePlugin'),
            ('192.168.0.2', 'SomePlugin'),
        }, union._private_ips)
        self.assertCountEqual([
            '192.168.0.1',
            '192.168.0.2'
        ], union.private_ips)

        self.assertCountEqual({
            ('200.0.0.2', 'SomePlugin')
        }, union._public_ips)
        self.assertCountEqual([
            '200.0.0.2'
        ], union.public_ips)

        self.assertCountEqual({
            'SomeResourcePlugin': {
                'SomeResourceID',
                'OtherResourceID'
            },
            'OtherResourcePlugin': {
                'OtherResourceID'
            }
        }, union.resources)


    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree('src'),
        os.rename('tmp', 'src')
        

if __name__ == '__main__':
    unittest.main()
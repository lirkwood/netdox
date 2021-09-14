from netdox import iptools
from pytest import raises

## Validation

def test_valid_ip():
    assert iptools.valid_ip('0.0.0.0')
    assert iptools.valid_ip('255.255.255.255')

    assert not iptools.valid_ip('0.0.0.0.0')
    assert not iptools.valid_ip('0.0.0')
    assert not iptools.valid_ip('255.255.256.255')

def test_valid_subnet():
    assert iptools.valid_subnet('0.0.0.0/0')
    assert iptools.valid_subnet('0.0.0.0/31')
    assert iptools.valid_subnet('255.255.255.255/0')
    assert iptools.valid_subnet('255.255.255.255/01')
    assert iptools.valid_subnet('255.255.255.255/31')

    assert not iptools.valid_subnet('255.255.255.255/32')
    assert not iptools.valid_subnet('255.255.255.255/001')

def test_valid_range():
    assert iptools.valid_range('0.0.0.0-0.0.0.1')
    assert iptools.valid_range('0.0.0.0-0.0.0.0')
    assert iptools.valid_range('0.0.0.0-255.255.255.255')
    assert iptools.valid_range('255.255.255.255-0.0.0.0')


## Subnet funcs

def test_subn_floor():
    assert iptools.subn_floor('255.255.255.255/0') == '0.0.0.0'
    assert iptools.subn_floor('255.255.255.255/1') == '128.0.0.0'
    assert iptools.subn_floor('255.255.255.255/16') == '255.255.0.0'
    assert iptools.subn_floor('255.255.255.255/31') == '255.255.255.254'

def test_subn_bounds():
    bounds = lambda lower, upper: {'lower':lower,'upper':upper}

    assert iptools.subn_bounds('0.0.0.0/0') == bounds('0.0.0.0','255.255.255.255')
    assert iptools.subn_bounds('0.0.0.0/16') == bounds('0.0.0.0','0.0.255.255')
    assert iptools.subn_bounds('0.0.0.0/31') == bounds('0.0.0.0','0.0.0.1')
    assert iptools.subn_bounds('128.255.255.255/1') == bounds('128.0.0.0','255.255.255.255')

    assert iptools.subn_bounds('0.0.0.0/0', integer = True) == bounds(
        iptools.cidr2int('0.0.0.0'), iptools.cidr2int('255.255.255.255')
    )
    assert iptools.subn_bounds('0.0.0.0/16', integer = True) == bounds(
        iptools.cidr2int('0.0.0.0'), iptools.cidr2int('0.0.255.255')
    )

def test_subn_equiv():
    assert iptools.subn_equiv('0.0.0.0/24', 25) == [
        '0.0.0.0/25', '0.0.0.128/25'
    ]
    assert iptools.subn_equiv('0.0.0.0/17', 20) == [
        '0.0.0.0/20', 
        '0.0.16.0/20', 
        '0.0.32.0/20',
        '0.0.48.0/20', 
        '0.0.64.0/20', 
        '0.0.80.0/20',
        '0.0.96.0/20', 
        '0.0.112.0/20',
    ]

    assert iptools.subn_equiv('0.0.0.0/17', 16) == ['0.0.0.0/16']

    with raises(ValueError):
        iptools.subn_equiv('0.0.0.999/16', 17)

def test_subn_contains():
    assert iptools.subn_contains('0.0.0.0/0', '0.0.0.0')
    assert iptools.subn_contains('0.0.0.0/0', '255.255.255.255')

    assert iptools.subn_contains('0.0.0.0/16', '0.0.0.0')
    assert iptools.subn_contains('0.0.0.0/16', '0.0.255.255')

    assert iptools.subn_contains('0.0.0.0/24', '0.0.0.0/25')
    assert iptools.subn_contains('0.0.0.0/24', '0.0.0.128/25')

    assert not iptools.subn_contains('0.0.0.0/1', '128.0.0.0')
    assert not iptools.subn_contains('0.0.0.0/16', '0.1.0.0/24')

    with raises(ValueError):
        iptools.subn_contains('0.0.0.0/16', 'not a valid ip or subnet')


## Iteration

def test_subn_iter():
    assert [
        ip for ip in iptools.subn_iter('0.0.0.0/24')
    ] == [
        f'0.0.0.{i}' for i in range(256)
    ]

    assert [
        ip for ip in iptools.subn_iter('0.0.255.255/16')
    ] == [
        f'0.0.{third}.{fourth}' 
        for third in range(256) for fourth in range(256)
    ]

def test_range_iter():
    assert [
        ip for ip in iptools.range_iter('0.0.0.0','0.0.0.255')
    ] == [
        f'0.0.0.{i}' for i in range(256)
    ]

    assert [
        ip for ip in iptools.range_iter('0.0.0.0','0.0.255.255')
    ] == [
        f'0.0.{third}.{fourth}' 
        for third in range(256) for fourth in range(256)
    ]


## Conversion

def test_cidr2int():
    assert iptools.cidr2int('0.0.0.0') == 0
    assert iptools.cidr2int('255.255.255.255') == (256 ** 4) - 1
    assert iptools.cidr2int('123.45.67.89') == 89 + (67 * 256) + (45 * (256 ** 2)) + (123 * (256 ** 3))

def test_int2cidr():
    assert iptools.int2cidr(0) == '0.0.0.0'
    assert iptools.int2cidr((256 ** 4) - 1) == '255.255.255.255'
    assert iptools.int2cidr(89 + (67 * 256) + (45 * (256 ** 2)) + (123 * (256 ** 3))) == '123.45.67.89'


## Other

def test_public_ip():
    assert iptools.public_ip('0.0.0.0')
    assert iptools.public_ip('255.255.255.255')

    assert not iptools.public_ip('192.168.0.0')
    assert not iptools.public_ip('192.168.255.255')

    assert not iptools.public_ip('10.0.0.0')
    assert not iptools.public_ip('10.255.255.255')

    assert not iptools.public_ip('172.16.0.0')
    assert not iptools.public_ip('172.31.255.255')

def test_search_string():
    assert iptools.search_string('0.0.0.0\n255.255.255.255') == ['0.0.0.0','255.255.255.255']
    assert iptools.search_string('aaaaaaaa|0.0.0.0|aaaaaaaa', delimiter = '|') == ['0.0.0.0']

    threesubns = """0.0.0.0/0
    0.0.0.0/16
    0.0.0.0/31"""

    assert iptools.search_string(threesubns, 'ipv4') == []
    assert iptools.search_string(threesubns, 'ipv4_range') == []
    assert iptools.search_string(threesubns, 'ipv4_subnet') == [
        '0.0.0.0/0',
        '0.0.0.0/16',
        '0.0.0.0/31'
    ]

    threeranges = """0.0.0.0-128.0.0.0
    0.0.0.0-255.0.0.0
    128.0.255.255-128.255.255.255"""

    assert iptools.search_string(threeranges, 'ipv4') == []
    assert iptools.search_string(threeranges, 'ipv4_subnet') == []
    assert iptools.search_string(threeranges, 'ipv4_range') == [
        '0.0.0.0-128.0.0.0',
        '0.0.0.0-255.0.0.0',
        '128.0.255.255-128.255.255.255'
    ]

    with raises(ValueError):
        iptools.search_string(threeranges, 'ipv6')

def test_sort():
    assert iptools.sort('0.0.0.0') == '0.0.0.0/24'
    assert iptools.sort('0.0.0.255') == '0.0.0.0/24'

    assert iptools.sort('0.0.0.0', 25) == '0.0.0.0/25'
    assert iptools.sort('0.0.0.127', 25) == '0.0.0.0/25'
    assert iptools.sort('0.0.0.128', 25) == '0.0.0.128/25'
    assert iptools.sort('0.0.0.255', 25) == '0.0.0.128/25'
    
    assert iptools.sort('123.45.67.89', 16) == '123.45.0.0/16'

def test_collapse_iplist():
    iplist = [
        'invalid.ip.address',
        '123.456.789.101',
        '255.255.255.127',
        '0.0.0.252',
        '0.0.0.0',
        '0.0.0.255',
        '0.0.0.1',
        '255.255.255.129',
        '0.0.0.254',
        '0.0.0.253',
        '0.0.0.2',
        '255.255.255.128'
    ]
    assert iptools.collapse_iplist(iplist, output = 'ranges') == [
        '0.0.0.0-0.0.0.2',
        '0.0.0.252-0.0.0.255',
        '255.255.255.127-255.255.255.129'
    ]
    assert iptools.collapse_iplist(iplist, output = 'subnets') == [
        '0.0.0.0/31',
        '0.0.0.2',
        '0.0.0.252/30',
        '255.255.255.127',
        '255.255.255.128/31'
    ]

    with raises(ValueError):
        iptools.collapse_iplist(iplist, output = 'invalid value')
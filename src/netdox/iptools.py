"""
Module of useful functions for manipulating IPv4 addresses, subnets, and ranges.
"""

import math
import re
from collections import deque
from typing import Any, Generator, Iterable, Union

####################
# Module functions #
####################

## Useful regex patterns

regex_ip = re.compile(r'((1?[0-9]{0,2}|2[0-4][0-9]|25[0-5])\.){3}(1?[0-9]{0,2}|2[0-4][0-9]|25[0-5])')
regex_subnet = re.compile(rf'{regex_ip.pattern}/([0-2]?[0-9]|3[0-1])')
regex_range = re.compile(rf'{regex_ip.pattern}-{regex_ip.pattern}')


## Validation

def valid_ip(string: str) -> bool:
    """
    Tests if a string is valid as a CIDR IPv4 address.

    :param string: The string to test.
    :type string: str
    :return: A boolean. True if *string* is a valid CIDR IPv4 address.
    :rtype: bool
    """
    if re.fullmatch(regex_ip, string):
        return True
    else:
        return False
    
def valid_subnet(string: str) -> bool:
    """
    Tests if a string is valid as a CIDR IPv4 subnet.

    :param string: The string to test.
    :type string: str
    :return: A boolean. True if *string* is a valid CIDR IPv4 subnet.
    :rtype: bool
    """
    if re.fullmatch(regex_subnet, string):
        return True
    else:
        return False

def valid_range(string: str) -> bool:
    """
    Tests if a string is valid as a CIDR IPv4 range.

    :param string: The string to test.
    :type string: str
    :return: A boolean. True if *string* is a valid CIDR IPv4 range.
    :rtype: bool
    """
    if re.fullmatch(regex_range, string):
        return True
    else:
        return False

def public_ip(ipv4: str) -> bool:
    """
    Tests if an IP address is part of the public or private namespace

    :param ipv4: The IPv4 address to test, in CIDR form
    :type ipv4: str
    :return: A boolean. True if *ipv4* is a public IP.
    :rtype: bool
    """
    if subn_contains('192.168.0.0/16', ipv4):
        return False
    elif subn_contains('10.0.0.0/8', ipv4):
        return False
    elif subn_contains('172.16.0.0/12', ipv4):
        return False
    else:
        return True


## Subnet functions

def subn_floor(subn: str) -> str:
    """
    Returns the lowest IP address in a subnet

    :param subn: An IPv4 subnet to find the floor of, in CIDR form.
    :type subn: str
    :return: An IPv4 address in CIDR form.
    :rtype: str
    """
    mask = int(subn.split('/')[-1])
    addr = subn.split('/')[0]
    octets = addr.split('.')
    for octet in range(4):
        octets[octet] = int(octets[octet])

    split_octet = mask // 8
    
    octet_mask = mask % 8
    if octet_mask:
        octets[split_octet] >>= 8 - octet_mask
        octets[split_octet] <<= 8 - octet_mask  # discard all bits after mask
    else:
        octets[split_octet] = 0

    str_octets = []
    for octet in range(4):
        if octet > split_octet:
            octets[octet] = 0
        str_octets.append(str(octets[octet]))
            
    min_addr = '.'.join(str_octets)
    return min_addr

def subn_bounds(subn: str, integer: bool = False) -> dict[str, Union[str, int]]:
    """
    Returns a dictionary of the bounds of a subnet, as integers

    :param subn: An IPv4 subnet to find the bounds of, in CIDR form.
    :type subn: str
    :param integer: Whether to return the bounds as an integer instead of a string in CIDR form, defaults to False
    :type integer: bool, optional
    :return: A dictionary with keys 'upper' and 'lower' of the bounds of *subn*.
    :rtype: dict[str, Union[str, int]]
    """
    lower = cidr2int(subn_floor(subn))
    bounds = {'lower': lower}

    mask = int(subn.split('/')[-1])

    upper = lower
    for bit in range(32 - mask):
        upper += 2**bit    #set all bits out of mask range
    bounds['upper'] = upper

    if not integer:
        for bound in bounds:
            bounds[bound] = int2cidr(bounds[bound])

    return bounds
    
def subn_equiv(subn: str, new_mask: int) -> list[str]:
    """
    Converts a subnet to new subnet(s) with the given mask.

    :param subn: An IPv4 subnet to convert, in CIDR form.
    :type subn: str
    :param new_mask: The new bit mask to apply to the subnet.
    :type new_mask: int
    :raises ValueError: If *subn* is not a valid IPv4 subnet.
    :return: A list of IPv4 subnets in CIDR form, with an equivalent address space to *subn*.
    :rtype: list[str]
    """
    if valid_subnet(subn):
        old_mask = int(subn.split('/')[-1])
    else:
        raise ValueError('Cannot find equivalent subnets to invalid subnet.')
    subnets = []
    int_min_addr = cidr2int(subn_floor(subn))

    if new_mask > old_mask:
        for _ in range(2**(new_mask - old_mask)):
            min_addr = int2cidr(int_min_addr)
            new_subnet = min_addr +'/'+ str(new_mask)
            subnets.append(new_subnet)

            int_min_addr += (2**(32-new_mask))
    else:
        new_subnet = subn_floor(subn) +'/'+ str(new_mask)
        subnets.append(subn_floor(new_subnet) +'/'+ str(new_mask))

    return subnets

def subn_contains(subn: str, object: str) -> bool:
    """
    Tests if a subnet contains an IP or subnet.

    :param subn: The IPv4 subnet that may or may not contain *object*, in CIDR form.
    :type subn: str
    :param object: The object that may or may not be contained in *subn*, either an IPv4 address or subnet, in CIDR form.
    :type object: str
    :raises ValueError: If object is not a valid IPv4 address or subnet.
    :return: A boolean. True if *subn* does contain *object*.
    :rtype: bool
    """
    if valid_ip(object):
        ip = object
    elif valid_subnet(object):
        bounds = subn_bounds(object)
        return (subn_contains(subn, bounds['upper']) & subn_contains(subn, bounds['lower']))
    else:
        raise ValueError(f'Object to be tested must be a valid ipv4 or subnet.')

    bin_ip = cidr2int(ip)
    bounds = subn_bounds(subn, integer=True)
    if bin_ip >= int(bounds['lower']) and bin_ip <= int(bounds['upper']):
        return True
    else:
        return False
    
def subn_iter(subn: str) -> Generator[str, Any, Any]:
    """
    Returns a generator which yields each IP address in a subnet, lowest first.
    Internally, calls ranger_iter on the bounds of the subnet.

    :param subn: An IPv4 subnet, as a string, in CIDR form.
    :type subn: str
    :yield: Each IPv4 address in the subnet, as a string.
    :rtype: Generator[str, Any, Any]
    """
    for ip in range_iter(**subn_bounds(subn)):
        yield ip


## Conversion functions

def cidr2int(ipv4: str) -> int:
    """
    Converts an IPv4 address provided as a string in CIDR form, to an integer.

    :param ipv4: An IPv4 address as a string in CIDR form.
    :type ipv4: str
    :return: The same IPv4 address as an integer.
    :rtype: int
    """
    octets = ipv4.split('.')
    int_ip = 0
    for octet in range(4):
        int_ip += int(octets[octet]) << (8 * (3 - octet))
    return int_ip

def int2cidr(ipv4: int) -> str:
    """
    Converts an IPv4 address provided as an integer, to a string in CIDR form.

    :param ipv4: An IPv4 address as an integer
    :type ipv4: int
    :return: The same IPv4 address as a string in CIDR format.
    :rtype: str
    """
    bin_str = bin(ipv4)[2:].zfill(32)
    str_octets = [str(int(bin_str[octet:octet+8], base = 2)) for octet in range(0,32,8)]
    return '.'.join(str_octets)


## Other

def range_iter(lower: Union[str, int], upper: Union[str, int]) -> Generator[str, Any, Any]:
    """
    Iterates over the IPv4 addresses in an IP range.

    :param lower: The lower bound of the range as an IPv4 address, either as an integer or as a string in CIDR format.
    :type lower: Union[str, int]
    :param upper: The upper bound of the range as an IPv4 address, either as an integer or as a string in CIDR format.
    :type upper: Union[str, int]
    :yield: Each IPv4 address in the range between lower and upper, inclusive, from starting from lower.
    :rtype: Generator[str, Any, Any]
    """
    if isinstance(lower, str):
        lower = cidr2int(lower)
    if isinstance(upper, str):
        upper = cidr2int(upper)
    if lower > upper: lower, upper = upper, lower
    current = lower
    while current <= upper:
        yield int2cidr(current)
        current += 1

def search_string(string: str, object: str = 'ipv4', delimiter: str = None) -> list[str]:
    """
    Searches a string for all instances of type *object*.
    Searches in chunks delimited by the provided value (default = newline).

    :param string: The string to search within.
    :type string: str
    :param object: The type of object to search for, one of ('ipv4' 'ipv4_subnet' 'ipv4_range'). Defaults to 'ipv4'
    :type object: str, optional
    :param delimiter: The delimiter to split *string* on, defaults to None
    :type delimiter: str, optional
    :raises ValueError: If *output* takes a value that is not one of: 'ipv4', 'ipv4_subnet', 'ipv4_range'.
    :return: A list of objects found within the string.
    :rtype: list[str]
    """
    if object == 'ipv4':
        validate = valid_ip
    elif object == 'ipv4_subnet':
        validate = valid_subnet
    elif object == 'ipv4_range':
        validate = valid_range
    else:
        raise ValueError(f'Search object must be one of: ipv4, ipv4_subnet; Not {object}')

    outlist = []
    for line in string.split(delimiter):
        # Ignore comments
        if not (line.startswith('#') or line.startswith('//')):
            cleanline = line.strip()
            if validate(cleanline):
                outlist.append(cleanline)
    outlist = list(dict.fromkeys(outlist))
    return outlist


def sort(ip: str, mask: int = 24) -> str:
    """
    Returns the subnet with a given mask an IPv4 address is in

    :param ip: An IPv4 address in CIDR format.
    :type ip: str
    :param mask: The subnet mask to use in bits, defaults to 24
    :type mask: int, optional
    :return: An IPv4 subnet in CIDR format.
    :rtype: str
    """
    mask = str(mask)
    subn = ip +'/'+ str(mask)
    return f'{subn_floor(subn)}/{str(mask)}'


def collapse_iplist(iplist: Iterable[str], output = 'ranges') -> list[str]:
    """
    Scans a list of IPv4 addresses and replaces consecutive addresses with an equivalent range or subnet.

    2do: collapse consecutive subnets aswell

    :param iplist: An iterable object containing IPv4 addresses as strings.
    :type iplist: Iterable[str]
    :param output: A string defining the type of object to collapse the IPs to, defaults to 'ranges'
    :type output: str, optional
    :raises ValueError: If *output* is not one of: 'ranges', 'subnets'.
    :return: A list of IPv4 addresses and IPv4 ranges / subnets
    :rtype: list[str]
    """
    if output not in ('ranges', 'subnets'):
        raise ValueError(f'Unknown output mode: {output}. Must be one of: ranges, subnets.')
    # get unique, sorted deque of ips as integers
    ipdeque = deque(sorted(set([cidr2int(ip) for ip in iplist if valid_ip(ip)])))
    minlist = []
    while ipdeque:
        ip = ipdeque.popleft()
        currentInt = ip
        currentSubn = [ip]
        for nextint in ipdeque:
            if output == 'subnets':
                nextmask = math.ceil(math.log2(len(currentSubn) + 1))
                octet4 = int(int2cidr(ip).split('.')[-1])
                if not octet4 % (2**nextmask) == 0:
                    break
            if nextint == currentInt + 1:
                currentInt = nextint
                currentSubn.append(nextint)
            else:
                break

        if len(currentSubn) == 1:
            currentSubn.pop()

        if currentSubn:
            if output == 'subnets':
                while not math.log2(len(currentSubn)).is_integer():
                    currentSubn.pop()
                mask = int(32 - math.log2(len(currentSubn)))
                minlist.append(f'{int2cidr(currentSubn[0])}/{mask}')
            else:
                minlist.append(f'{int2cidr(ip)}-{int2cidr(currentSubn[-1])}')
            for _ in range(len(currentSubn) - 1):
                ipdeque.popleft()
        else:
            minlist.append(int2cidr(ip))
    
    return minlist
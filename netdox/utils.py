import iptools, json, re
from traceback import format_exc
from datetime import datetime


class dns:
    name: str
    root: str
    source: str

    """
    Class representing some DNS record
    """

    def __init__(self, name, root=None, source=None):
        if re.fullmatch('([a-zA-Z0-9_-]+\.)+[a-zA-Z0-9_-]+', name):
            self.name = name.lower()
            if root: self.root = root.lower()
            self.source = source

            # destinations
            self.public_ips = set()
            self.private_ips = set()
            self.domains = set()
            self.vms = set()
            self.apps = set()
            self.nat = set()

            self.subnets = set()
        else:
            raise ValueError('Must provide a valid name for dns record (some FQDN)')

    # switch to case match on 2021-04-10
    def link(self, string, type):
        """
        Adds a destination which this DNS record points to
        """
        if isinstance(string, str):
            string = string.lower().strip()
            if type == 'ipv4' or type == 'ip':
                if iptools.valid_ip(string):
                    self.subnets.add(iptools.sort(string))
                    if iptools.public_ip(string):
                        self.public_ips.add(string)
                    else:
                        self.private_ips.add(string)
                else:
                    raise ValueError(f'"{string}" is not a valid ipv4 address.')

            elif type == 'nat':
                if re.fullmatch('([a-zA-Z0-9_-]+\.)+[a-zA-Z0-9_-]+', string):
                    self.nat.add(string)

            elif type == 'domain':
                if re.fullmatch('([a-zA-Z0-9_-]+\.)+[a-zA-Z0-9_-]+', string):
                    self.domains.add(string)
            
            elif type == 'vm':
                self.vms.add(string)
            
            elif type == 'app':
                self.apps.add(string)

            else:
                raise ValueError('Provide a valid destination type. One of: "ipv4", "domain')

        else:
            raise TypeError('DNS destination must be provided as string')

    @property
    def destinations(self):
        return {
            'public_ips': self.public_ips,
            'private_ips': self.private_ips,
            'domains': self.domains,
            'vms': self.vms,
            'apps': self.apps,
            'nat': self.nat
        }

    @property
    def ips(self):
        return self.public_ips.union(self.private_ips)

    def fetch_subnets(self):
        for ip in self.ips:
            self.subnets.add(iptools.sort(ip))

def merge_sets(dns1,dns2):
    """
    Simple merge of any sets of found in two dns objects
    """
    if isinstance(dns1, dns) and isinstance(dns2,dns):
        dns1_inf = dns1.__dict__
        dns2_inf = dns2.__dict__
        for attr in dns2_inf:
            if isinstance(dns2_inf[attr], set):
                dns1_inf[attr] = dns1_inf[attr].union(dns2_inf[attr])
        return dns1
    else:
        raise TypeError(f'Arguments must be dns objects, not {type(dns1)}, {type(dns2)}')




class JSONEncoder(json.JSONEncoder):
    """
    Default json encoder except set type is encoded as list
    """
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


def critical(func):
    funcname = func.__name__
    funcmodule = func.__module__
    if funcmodule == '__main__':
        funcmodule = 'netdox'
    def wrapper(*args, **kwargs):
        print(f'[DEBUG][netdox.py] [{datetime.now()}] Function {funcmodule}.{funcname} was called')
        try:
            returned = func(*args, **kwargs)
        except Exception as e:
            print(f'[ERROR][netdox.py] Essential function {funcmodule}.{funcname} threw an exception:\n')
            raise e
        else:
            print(f'[DEBUG][netdox.py] [{datetime.now()}] Function {funcmodule}.{funcname} returned')
            return returned
    return wrapper

def handle(func):
    funcname = func.__name__
    funcmodule = func.__module__
    if funcmodule == '__main__':
        funcmodule = 'netdox'
    def wrapper(*args, **kwargs):
        print(f'[DEBUG][netdox.py] [{datetime.now()}] Function {funcmodule}.{funcname} was called')
        try:
            returned = func(*args, **kwargs)
        except Exception:
            print(f'[WARNING][netdox.py] Function {funcmodule}.{funcname} threw an exception:\n\n {format_exc()}')
            return None
        else:
            print(f'[DEBUG][netdox.py] [{datetime.now()}] Function {funcmodule}.{funcname} returned')
            return returned
    return wrapper

def silent(func):
    funcname = func.__name__
    funcmodule = func.__module__
    if funcmodule == '__main__':
        funcmodule = 'netdox'
    def wrapper(*args, **kwargs):
        try:
            returned = func(*args, **kwargs)
        except Exception:
            print(f'[WARNING][netdox.py] Function {funcname} from module {funcmodule} threw an exception:\n\n {format_exc()}')
            return None
        else:
            return returned
    return wrapper
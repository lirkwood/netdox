import iptools, json, re


            # if iptools.valid_ip(string) or re.fullmatch('([a-zA-Z0-9_-]\.)+[a-zA-Z0-9_-]', string):
            #     self._destinations.append(string)
            # else:
            #     raise TypeError('DNS destination must be one of: ip, domain')


class dns:
    name: str
    root: str
    source: str

    def __init__(self, name, root=None, source=None):
        if re.fullmatch('([a-zA-Z0-9_-]+\.)+[a-zA-Z0-9_-]+', name):
            self.name = name
            self.root = root
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
                    if iptools.is_public(string):
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

def merge(dns1,dns2):
    """
    Simple merge of two dns objects
    """
    if isinstance(dns1, dns) and isinstance(dns2,dns):
        dns1.destinations.update(dns2.destinations)
        return dns1
    else:
        raise TypeError(f'Arguments must be dns objects, not {type(dns1)}, {type(dns2)}')




class JSONEncoder(json.JSONEncoder):
    """
    Default json encoder except set type is encoded as list
    """
    def default(self, obj):
        if isinstance(obj, (list, dict, str, int, float, bool, type(None))):
            return json.JSONEncoder.default(self, obj)
        elif isinstance(obj, set):
            return json.JSONEncoder.default(self, list(obj))
        else:
            raise TypeError(f'Object of type {type(obj)} is not JSON serializable')
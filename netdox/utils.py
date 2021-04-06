import iptools, re


            # if iptools.valid_ip(string) or re.fullmatch('([a-zA-Z0-9_-]\.)+[a-zA-Z0-9_-]', string):
            #     self._destinations.append(string)
            # else:
            #     raise TypeError('DNS destination must be one of: ip, domain')


class dns:
    name: str
    _destinations: dict

    def __init__(self, name):
        if re.fullmatch('([a-zA-Z0-9_-]\.)+[a-zA-Z0-9_-]', name):
            self.name = name
            self._destinations = {
                'public_ips':[],
                'private_ips': [],
                'domains': [],
                'vms': [],
                'apps': [],
                'nat': []
                }

    @property
    def destinations(self):
        return self._destinations

    # switch to case match on 2021-04-10
    @destinations.setter
    def destinations(self, string, type):
        if isinstance(string, str):
            if type == 'ipv4':
                if iptools.valid_ip(string):
                    if iptools.is_public(string):
                        self._destinations['public_ips'].append(string)
                    else:
                        self._destinations['private_ips'].append(string)
                else:
                    raise ValueError(f'"{string}" is not a valid ipv4 address.')

            elif type == 'nat':
                if iptools.valid_ip(string):
                    self._destinations['nat'].append(string)
                else:
                    raise ValueError(f'"{string}" is not a valid ipv4 address.')

            elif type == 'domain':
                if re.fullmatch('([a-zA-Z0-9_-]\.)+[a-zA-Z0-9_-]', string):
                    self._destinations['domains'].append(string)
            
            elif type == 'vm':
                self._destinations['vms'].append(string)
            
            elif type == 'app':
                self._destinations['apps'].append(string)

            else:
                raise ValueError('Provide a valid destination type. One of: "ipv4", "domain')

        else:
            raise TypeError('DNS destination must be provided as string')
    
    @destinations.deleter
    def destinations(self, string):
        if isinstance(string, str):
            if iptools.valid_ip(string) or re.fullmatch('([a-zA-Z0-9_-]\.)+[a-zA-Z0-9_-]', string):
                if string in self._destinations:
                    self._destinations.remove(string)
                else:
                    raise ValueError(f'Destination {string} not present.')
            else:
                raise TypeError('DNS destination must be one of: ip, domain')
        else:
            raise TypeError('DNS destination must be provided as string')
    

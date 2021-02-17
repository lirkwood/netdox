import json
import os

def main():
    with open('src/apps.json','r') as stream:
        master = {}
        jsondata = json.load(stream)
        for context in jsondata:
            for _app in jsondata[context]:
                app = jsondata[context][_app]
                try:
                    for domain in app['domains']:
                        if domain not in master:
                            master[domain] = {'dest': {'ips': [], 'domains': [], 'apps': []}, 'root': '', 'source': 'Kubernetes'}
                        master[domain]['dest']['apps'].append(_app)
                except KeyError:
                    pass
        
        return master
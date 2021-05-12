import utils
import json

@utils.critical
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
                            master[domain] = utils.dns(domain, source='Kubernetes')
                        master[domain].link(_app, 'app')
                        if 'locations' in utils.auth['kubernetes'][context] and utils.auth['kubernetes'][context]['locations']:
                            master[domain].location = utils.auth['kubernetes'][context]['locations'][0]
                        else:
                            print(f'[WARNING][k8s_domains.py] Cluster {context} has no location data.')
                except KeyError:
                    pass
        
        return master
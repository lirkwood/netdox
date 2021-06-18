from plugins.kubernetes import initContext
from kubernetes.client.rest import ApiException
from kubernetes import client
from bs4 import BeautifulSoup
from typing import Union
from flask import Response
import json, yaml, re
import pageseeder


def app_action(uri, status):
    """
    Delegates to downstream functions based on workflow status
    """
    name = BeautifulSoup(pageseeder.get_fragment(uri, 'title'), features='xml').find('heading').string
    uriDetails = json.loads(pageseeder.get_uri(uri))

    ## Find cluster
    path = uriDetails['decodedpath'].split('/')
    cluster = path[-2]

    if status == 'Approved':
        create_app(name, cluster, uri)
    elif status == 'Suspended':
        scale_app(name, cluster, 0)
        

# 2do: add replicas spec
def create_app(name: str, cluster: str, uri: Union[str, int]):
    """
    Used to create apps from a combination of boilerplate yaml and properties from a PageSeeder document
    """
    ## Container info
    containers = []
    container = None
    volume = None
    while True:
        hasPrefix = BeautifulSoup(pageseeder.get_fragment(uri, f'container_{len(containers) + 1}'), features='xml')
        noPrefix = BeautifulSoup(pageseeder.get_fragment(uri, f'{len(containers) + 1}'), features='xml')
        containerPSML = None
        for response in (hasPrefix, noPrefix):
            if response.find('properties-fragment'):
                containerPSML = response
        if not containerPSML:
            break

        for property in containerPSML('property'):
            if property['name'] == 'container':
                containers.append({
                    'name': property['value'],
                    'volumes': {}
                })
                container = containers[-1]
            
            elif property['name'] == 'image':
                container['imageLink'] = property['value']
                imageInf = re.search(r'registry-gitlab.allette.com.au/([a-zA-Z0-9-]+/)*(?P<project>[a-zA-Z0-9-]+):(?P<tag>.*)$',
                                    container['imageLink'])
                container['project'] = imageInf['project']
                container['imageTag'] = imageInf['tag']

            elif property['name'] == 'pvc':
                container['volumes'][property['value']] = {}
                volume = container['volumes'][list(container['volumes'])[-1]]

            elif property['name'] == 'mount_path':
                volume['mount_path'] = property['value']
            elif property['name'] == 'sub_path':
                volume['sub_path'] = property['value']

    ## Find any domains for ingress
    domainFrag = BeautifulSoup(pageseeder.get_fragment(uri, 'domains'), features='xml')
    domains = []
    for property in domainFrag('property'):
        domains.append(property.xref.string)


    if len(containers) != 1:
        if len(containers) > 1:
            raise NotImplementedError('Creating deployments with multiple containers has not been implemented yet.')
        else:
            raise ValueError('At least one container spec is required')
    else:
        container = containers[0]
        if container['project'] == 'psberlioz-simple':
            create_simple(name, container, domains, cluster)

    return Response(status=201)

def scale_app(name: str, cluster: str, replicas: int):
    """
    Used to modify the number of replicas of an app
    """
    apiClient = initContext(cluster)
    api = client.AppsV1Api(apiClient)
    body = {
        'api_version': 'autoscaling/v1',
        'kind': 'Scale',
        'spec': {
            'replicas': replicas
        }
    }
    api.patch_namespaced_deployment_scale(name = name, namespace = 'default', body = body)
    print(f'[INFO][kubernetes] Scaled {name} to {replicas} replicas')


##########################
# App specific functions #
##########################

def create_simple(name: str, container: dict, domains: list, cluster: str):
    """
    Downstream function for create_app if specified image ID is a berlioz simple site image
    """
    apiClient = initContext(cluster)

    volume = list(container['volumes'])[0]

    templateVals = {
        'depname': name,
        'domain': domains[0],
        'containername': container['name'],
        'image': container['imageLink'],
        'pvc': volume,
        'sub_path': container['volumes'][volume]['sub_path'],
        'mount_path': '/tmp/jetty/appdata'
    } 

    with open(f'plugins/kubernetes/src/templates/simple.yml', 'r') as stream:
        templateRaw = stream.read()

    for key, val in templateVals.items():
        templateRaw = re.sub(rf'<{key}>', val, templateRaw)
    
    deployment, service, ingress = [yaml.safe_load(template) for template in re.split(r'\n\s*---\s*\n', templateRaw)]

    api = client.AppsV1Api(apiClient)
    try:
        api.create_namespaced_deployment(body = deployment, namespace = 'default')
    except ApiException as e:
        depScale = api.read_namespaced_deployment_scale(name, namespace = 'default')
        if depScale.spec.replicas == 0:
            scale_app(name, cluster, 1)
        else:
            raise e
    else:
        print(f'[INFO][kubernetes] Created deployment {name}')

        api = client.CoreV1Api(apiClient)
        api.create_namespaced_service(body = service, namespace = 'default')
        print(f'[INFO][kubernetes] Created service for {name}')

        api = client.ExtensionsV1beta1Api(apiClient)
        api.create_namespaced_ingress(body = ingress, namespace = 'default')
        print(f'[INFO][kubernetes] Created ingress for {name}')

if __name__ == '__main__':
    scale_app('netdox-test-simple', 'dev', 0)
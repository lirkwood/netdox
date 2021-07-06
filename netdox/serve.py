from flask import Flask, request
from flask import Response

from traceback import format_exc, print_exc
from bs4 import BeautifulSoup
import subprocess, json, sys, re

import pageseeder, utils, iptools, plugins
from networkobjs import dns_name_pattern

app = Flask(__name__)

@app.route('/')
def root():
    return Response(status=200)

@app.route('/refresh', methods=['POST'])
def refresh():
    """
    Calls refresh
    """
    try:
        subprocess.run(executable = '/opt/app/netdox', args = ['refresh'], shell = True)
    except subprocess.CalledProcessError:
        return Response(status=500)
    return Response(status=200)

@app.route('/webhooks', methods=['POST'])
def webhooks():
    """
    Main route for PageSeeder webhooks. Sorts events and sends them to downstream functions
    """
    try:
        if request.content_length and request.content_length < 10**6 and request.is_json:
            body = request.get_json()
            for event in body['webevents']:
                    
                if event['type'] == 'webhook.ping':
                    return Response(status=200, headers=[('X-Ps-Secret', request.headers['X-PS-Secret'])])

                elif event['type'] == 'workflow.updated':
                    return workflow_updated(event)
            else:
                return Response(status=400)
        return Response(status=200)
    except Exception:
        print(f'[WARNING][webhooks] Threw exception:\n {format_exc()}')
        return Response(status=500)


def workflow_updated(event):
    """
    Main route. If workflow is 'Approved' netdox attempts to realise the links in the document.
    """
    status = event['workflow']['status']
    if status in ('Approved', 'Suspended'):
        comment = event['workflow']['comments'][0]
        comment_details = json.loads(pageseeder.get_comment(comment['id']))
        document_uri = comment_details['context']['uri']['id']
        document_type = comment_details['context']['uri']['documenttype']

        if document_type in ('domain' 'ip'):
            if status == 'Approved':
                if document_type == 'dns':
                    return approved_domain(document_uri)

                elif document_type == 'ip':
                    return approved_ip(document_uri)

        elif document_type == 'node':
            summary = pageseeder.pfrag2dict(pageseeder.get_fragment(document_uri, 'summary'))
            node_type = summary['type']
            if document_type in doctypeMap:
                plugin = pluginmaster.nodemap[node_type]
                try:
                    print(f'[INFO][webhooks] Delegating to {plugin.name} for node type {node_type}')
                    return plugin.approved_node(document_uri)
                except Exception:
                    print_exc()
                    return Response(status=500)
            else:
                print(f'[ERROR][webhooks] No function has been specified for the document type {document_type}')
                return Response(status=500)


def approved_domain(uri):
    """
    Handles ratifying changes specified in a DNS document.
    """
    info = pageseeder.pfrag2dict(pageseeder.get_fragment(uri, 'info'))
    links = BeautifulSoup(pageseeder.get_xref_tree(uri), features='xml')
        
    if 'name' in info and 'root' in info and info['name'] and info['root']:
        for link in links("xref"):
            try:
                if not (hasattr(link, 'unresolved') and link['unresolved'] == 'true'):
                    if link['type'] in ('ipv4','cname'):
                        name = info['name']
                        value = link['urititle']
                        zone = info['root']

                        dest = pageseeder.pfrag2dict(pageseeder.get_fragment(uri, link.parent['id']))
                        sourcePlugin = dest['source'].lower()
                        if sourcePlugin in pluginmaster:
                            plugin = pluginmaster[sourcePlugin]
                            if link['type'] == 'ipv4':
                                if iptools.valid_ip(value):
                                    try:
                                        plugin.create_A(name, value, zone)
                                    except AttributeError:
                                        print(f'[ERROR][webhooks] Plugin {sourcePlugin} has no method for creating an A record.')
                            else:
                                if re.fullmatch(dns_name_pattern, value):
                                    if not value.endswith('.'):
                                        value += '.'
                                    try:
                                        plugin.create_CNAME(name, value, zone)
                                    except AttributeError:
                                        print(f'[ERROR][webhooks] Plugin {sourcePlugin} has no method for creating a CNAME record.')
                        else:
                            print(f'[WARNING][webhooks] Unrecognised plugin {sourcePlugin}')
            except Exception:
                print(f'[ERROR][webhooks] Failed to parse the following xref as a DNS link:\n{link.prettify()}')
    else:
        print('[ERROR][webhooks] Missing mandatory fields: name or root')

    return Response(status=201)


def approved_ip(uri):
    """
    Handles ratifying changes specified in an IP document.
    """
    info = pageseeder.pfrag2dict(pageseeder.get_fragment(uri, 'info'))
    links = BeautifulSoup(pageseeder.get_xref_tree(uri), features='xml')
    if 'ipv4' in info and info['ipv4']:
        for link in links("xref"):
            try:
                if not (hasattr(link, 'unresolved') and link['unresolved'] == 'true'):
                    ip = info['ipv4'].split('.')[-1]
                    value = link['urititle']
                    if re.fullmatch(utils.dns_name_pattern, value):
                        if not value.endswith('.'):
                            value += '.'
                        dest = pageseeder.pfrag2dict(pageseeder.get_fragment(uri, link.parent['id']))
                        sourcePlugin = dest['source'].lower()
                        if sourcePlugin in pluginmaster.pluginmap['all']:
                            plugin = pluginmaster.pluginmap['all'][sourcePlugin]
                            try:
                                plugin.create_PTR(ip, value)
                            except AttributeError:
                                print(f'[ERROR][webhooks] Plugin {sourcePlugin} has no method for creating a PTR record.')
                        else:
                            print(f'[WARNING][webhooks] Unrecognised plugin {sourcePlugin}')
                    else:
                        print(f'[ERROR][webhooks] Invalid PTR value: {value}. Must be a valid FQDN.')

            except Exception:
                print(f'[ERROR][webhooks] Failed to parse the following xref as a PTR link:\n{link.prettify()}')
    else:
        print('[ERROR][webhooks] Missing mandatory fields: ipv4')
                
    return Response(status=201)


# def approved_vm(uri):
#     """
#     Handles documents with 'xo_vm' type and workflow 'Approved'.
#     """
#     core_inf = pageseeder.psfrag2dict(pageseeder.get_fragment(uri, 'core'))
#     os_inf = pageseeder.psfrag2dict(pageseeder.get_fragment(uri, 'os_version'))
#     addr_soup = BeautifulSoup(pageseeder.get_fragment(uri, 'addresses'), features='xml')

#     addrs = set()
#     for property in addr_soup("property"):
#         if iptools.valid_ip(property.xref.string):
#             addrs.add(property.xref.string)

#     location = utils.locate(addrs)
#     if location:
#         ansible.icinga_set_host(addrs[0], location)

#     if os_inf['template']:
#         xo_api.createVM(os_inf['template'], core_inf['name'])
#     else:
#         raise ValueError('[ERROR][server.py] Must provide a valid template/VM/snapshot UUID.')

#     return Response(status=200)

doctypeMap = {} 
psproperties = {}
if 'gunicorn' in sys.argv[0]:
    pluginmaster = plugins.PluginManager()
    pluginmaster.initPlugins() 
    with open('src/pageseeder.properties', 'r') as stream:
        for line in stream.read().splitlines():
            property = re.match('(?P<key>.+?)=(?P<value>.+?)', line)
            if property:
                psproperties[property['key']] = property['value']

    try:
        with open('src/webhooks.json', 'r') as stream:
            doctypeMap = json.load(stream)
    except FileNotFoundError:
        print('[WARNING][webhooks] Webhooks config file not found')
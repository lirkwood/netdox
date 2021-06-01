from flask import Flask, request
from flask import Response

from traceback import format_exc
from bs4 import BeautifulSoup
import json, re

import ps_api, utils, iptools, pluginmaster

app = Flask(__name__)

@app.route('/')
def root():
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
                    print(json.dumps(body, indent=4))
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
    if status == 'Approved':
        comment = event['workflow']['comments'][0]
        comment_details = json.loads(ps_api.get_comment(comment['id']))
        document_uri = comment_details['context']['uri']['id']
        document_type = comment_details['context']['uri']['documenttype']

        if document_type == 'dns':
            return approved_dns(document_uri)

        elif document_type == 'ip':
            return approved_ip(document_uri)


def approved_dns(uri):
    """
    Handles ratifying changes specified in a DNS document.
    """
    info = ps_api.pfrag2dict(ps_api.get_fragment(uri, 'info'))
    links = BeautifulSoup(ps_api.get_xref_tree(uri), features='xml')
        
    if 'name' in info and 'root' in info and info['name'] and info['root']:
        for link in links("xref"):
            try:
                if not (hasattr(link, 'unresolved') and link['unresolved'] == 'true'):
                    if link['type'] in ('ipv4','cname'):
                        name = info['name']
                        value = link['urititle']
                        zone = info['root']

                        dest = ps_api.pfrag2dict(ps_api.get_fragment(uri, link.parent['id']))
                        sourcePlugin = dest['source'].lower()
                        if sourcePlugin in pluginmaster.pluginmap['all']:
                            plugin = pluginmaster.pluginmap['all'][sourcePlugin]
                            if link['type'] == 'ipv4':
                                if iptools.valid_ip(value):
                                    try:
                                        plugin.create_A(name, value, zone)
                                    except AttributeError:
                                        print(f'[ERROR][webhooks] Plugin {sourcePlugin} has no method for creating an A record.')
                            else:
                                if re.fullmatch(utils.dns_name_pattern, value):
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

    return Response(status=200)


def approved_ip(uri):
    """
    Handles ratifying changes specified in an IP document.
    """
    info = ps_api.pfrag2dict(ps_api.get_fragment(uri, 'info'))
    links = BeautifulSoup(ps_api.get_xref_tree(uri), features='xml')
    if 'ipv4' in info and info['ipv4']:
        for link in links("xref"):
            try:
                if not (hasattr(link, 'unresolved') and link['unresolved'] == 'true'):
                    ip = info['ipv4'].split('.')[-1]
                    value = link['urititle']
                    if re.fullmatch(utils.dns_name_pattern, value):
                        if not value.endswith('.'):
                            value += '.'
                        dest = ps_api.pfrag2dict(ps_api.get_fragment(uri, link.parent['id']))
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
                
    return Response(status=200)


# def approved_vm(uri):
#     """
#     Handles documents with 'xo_vm' type and workflow 'Approved'.
#     """
#     core_inf = ps_api.psfrag2dict(ps_api.get_fragment(uri, 'core'))
#     os_inf = ps_api.psfrag2dict(ps_api.get_fragment(uri, 'os_version'))
#     addr_soup = BeautifulSoup(ps_api.get_fragment(uri, 'addresses'), features='xml')

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

if __name__ == '__main__':    
    psproperties = {}
    with open('src/pageseeder.properties', 'r') as stream:
        for line in stream.read().splitlines():
            property = re.match('(?P<key>.+?)=(?P<value>.+?)', line)
            if property:
                psproperties[property['key']] = property['value']
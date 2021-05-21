from flask import Flask, request
from flask import Response

from traceback import format_exc
from bs4 import BeautifulSoup
import json, re

import ps_api, utils, iptools, pluginmaster

app = Flask(__name__)

psproperties = {}
with open('src/pageseeder.properties', 'r') as stream:
    for line in stream.read().splitlines():
        property = re.match('(?P<key>.+?)=(?P<value>.+?)', line)
        if property:
            psproperties[property['key']] = property['value']


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
                    return ps_workflow_updated(event)
                
                else:
                    print(json.dumps(body, indent=4))
            else:
                return Response(status=400)
        return Response(status=200)
    except Exception:
        print(f'[WARNING][webhooks] Threw exception:\n {format_exc()}')
        return Response(status=500)


def ps_workflow_updated(event):
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


def approved_dns(uri):
    """
    Handles documents with 'dns' type and worflow 'Approved'.
    """
    info = ps_api.pfrag2dict(ps_api.get_fragment(uri, 'info'))
    links = BeautifulSoup(ps_api.get_xref_tree(uri), features='xml')
    dns = utils.loadDNS('src/dns.json')
        
    if info['name'] and info['root']:
        for link in links("xref"):
            try:
                # if link is not unresolved
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
                                if iptools.valid_ip(value) and value not in dns[name].ips:
                                    try:
                                        plugin.create_A(name, value, zone)
                                    except AttributeError:
                                        print(f'[ERROR][webhooks] Plugin {sourcePlugin} has no method for creating an A record.')
                            else:
                                if re.fullmatch(utils.dns_name_pattern, value) and value not in dns[name].cnames:
                                    try:
                                        plugin.create_CNAME(name, value, zone)
                                    except AttributeError:
                                        print(f'[ERROR][webhooks] Plugin {sourcePlugin} has no method for creating an CNAME record.')
            except Exception:
                print(f'[ERROR][webhooks] Failed to parse the following xref as a DNS link:\n{link.prettify()}')

    return Response(status=200)

    
        # ## Generic approved DNS actions
        # for destination in destinations("property"):

        #     if destination['name'] == 'ipv4':
        #         ip = destination.xref.string
        #         if ip not in dns[info['name']].ips:
        #             if iptools.public_ip(ip):
        #                 ## Create public A record
        #                 pass
                    
        #             else:
        #                 ## Create private A record
        #                 pass

        #     elif destination['name'] == 'cname':
        #         value = destination.xref.string
        #         if ip not in dns[info['name']].ips:
        #             if info['source'] == 'DNSMadeEasy':
        #                 ## Create public CNAME
        #                 pass
                    
        #             elif info['source'] == 'ActiveDirectory':
        #                 ## Create private CNAME
        #                 pass

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
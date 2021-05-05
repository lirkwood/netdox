from flask import Flask, request
from flask import Response

from traceback import format_exc
from bs4 import BeautifulSoup
import json, re

import ansible, dnsme_api, ad_api, ps_api, xo_api
import utils, iptools

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
        if request.method == 'POST':
            if request.content_length and request.content_length < 10**6 and request.is_json:
                body = request.get_json()
                for event in body['webevents']:
                        
                    if event['type'] == 'webhook.ping':
                        return Response(status=200, headers=[('X-Ps-Secret', request.headers['X-PS-Secret'])])

                    elif event['type'] == 'uri.modified':
                        return ps_uri_modified(event)

                    elif event['type'] == 'workflow.updated':
                        return ps_workflow_updated(event)
                    
                    else:
                        print(json.dumps(body, indent=4))
                else:
                    return Response(status=400)
        return Response(status=200)
    except Exception:
        print(f'[WARNING][serve.py] Threw exception:\n {format_exc()}')
        return Response(status=500)


def ps_uri_modified(event):
    uri = event['uri']
    return Response(status=200)

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
        elif document_type == 'xo_vm':
            return approved_vm(document_uri)


def approved_dns(uri):
    """
    Handles documents with 'dns' type and worflow 'Approved'.
    """
    info = ps_api.pfrag2dict(ps_api.get_fragment(uri, 'info'))
    icinga = ps_api.pfrag2dict(ps_api.get_fragment(uri, 'icinga'))
    destinations = BeautifulSoup(ps_api.get_fragment(uri, 'dest'), features='xml')
        
    if info['name'] and info['root']:
        icinga_eval(info, icinga)

        for destination in destinations("property"):

            if destination['name'] == 'ipv4':
                ip = destination.xref.string
                if iptools.public_ip(ip):
                    dnsme_api.create_A(info['name'], info['root'], ip)
                    print(f'[INFO][serve.py] Created A record in DNSMadeEasy with name {info["name"]} and value {ip}')
                
                else:
                    ad_api.create_record(info['name'], ip, info['root'], 'A')
                    print(f'[INFO][serve.py] Created A record in ActiveDirectory with name {info["name"]} and value {ip}')

            elif destination['name'] == 'cname':
                if info['source'] == 'DNSMadeEasy':
                    dnsme_api.create_CNAME(info['name'], info['root'], destination.xref.string)
                    print(f'[INFO][serve.py] Created CNAME record in DNSMadeEasy with name {info["name"]} and value {destination.xref.string}')
                
                elif info['source'] == 'ActiveDirectory':
                    ad_api.create_record(info['name'], destination.xref.string, info['root'], 'CNAME')
                    print(f'[INFO][serve.py] Created CNAME record in ActiveDirectory with name {info["name"]} and value {destination.xref.string}')

    return Response(status=200)

def approved_vm(uri):
    """
    Handles documents with 'xo_vm' type and workflow 'Approved'.
    """
    core_inf = ps_api.psfrag2dict(ps_api.get_fragment(uri, 'core'))
    os_inf = ps_api.psfrag2dict(ps_api.get_fragment(uri, 'os_version'))
    addr_soup = BeautifulSoup(ps_api.get_fragment(uri, 'addresses'), features='xml')

    addrs = set()
    for property in addr_soup("property"):
        if iptools.valid_ip(property.xref.string):
            addrs.add(property.xref.string)

    location = utils.locate(addrs)
    if location:
        icinga_eval(addrs[0], location)

    if os_inf['template']:
        xo_api.createVM(os_inf['template'], core_inf['name'])
    else:
        raise ValueError('[ERROR][server.py] Must provide a UUID to use as template.')

    return Response(status=200)


@utils.handle
def icinga_eval(addr, location=None, icinga=None):
    try:
        ansible.icinga_add_generic(addr, location, icinga)
    except KeyError:
        raise AttributeError(f'[ERROR][serve.py] Unable to confirm monitor status for {addr}; Missing mandatory values.')
from flask import Flask, request
from flask import Response

from traceback import format_exc
from bs4 import BeautifulSoup
import json, re
import dnsme_api, ps_api

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
    try:
        if request.method == 'POST':
            if  request.content_length and request.content_length < 10**6 and request.is_json:
                body = request.get_json()
                for event in body['webevents']:
                        
                    if event['type'] == 'webhook.ping':
                        return ps_webhook_ping(request.headers['X-PS-Secret'])

                    elif event['type'] == 'uri.modified':
                        # return ps_uri_modified(event)
                        pass

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


def ps_webhook_ping(secret):
    response = Response(status=200, headers=[('X-Ps-Secret', secret)])
    return response

def ps_uri_modified(event):
    uri = event['uri']
    return Response(status=200)

def ps_workflow_updated(event):
    status = event['workflow']['status']
    if status == 'Approved':
        comment = event['workflow']['comments'][0]
        comment_details = json.loads(ps_api.get_comment(comment['id']))
        document_uri = comment_details['context']['uri']['id']
        document_type = comment_details['context']['uri']['documenttype']

        if document_type == 'dns':
            return approved_dns(document_uri)


def approved_dns(uri):
    info_soup = BeautifulSoup(ps_api.get_fragment(uri, 'info'), features='xml')
    destinations = BeautifulSoup(ps_api.get_fragment(uri, 'dest'), features='xml')
    info = {}
    for property in info_soup("property"):
        info[property['name']] = property['value']
    # if info has minimum details
    if info['name'] and info['root'] and info['source']:
        for destination in destinations("property"):
            if destination['name'] == 'ipv4':
                if info['source'] == 'DNSMadeEasy':
                    dnsme_api.create_A(info['name'], info['root'], destination.xref.string)

            elif destination['name'] == 'cname':
                if info['source'] == 'DNSMadeEasy':
                    dnsme_api.create_CNAME(info['name'], info['root'], destination.xref.string)

    return Response(status=200)
from flask import Flask, request
from flask import Response
import json, re
import ps_api

app = Flask(__name__)

psproperties = {}
with open('src/pageseeder.properties', 'r') as stream:
    for line in stream.read().splitlines():
        property = re.match('(?P<key>.+?)=(?P<value>.+?)', line)
        psproperties[property['key']] = property['value']


@app.route('/')
def root():
    return Response(status=200)

@app.route('/webhooks', methods=['POST'])
def webhooks():
    if request.method == 'POST':
        if request.content_length < 10**6 and request.is_json:
            body = request.get_json()
            if body and body['webhook']['name'] == 'netdox-backend':
                for event in body['webevents']:
                    if event['event'][0]['name'] == psproperties['group']:
                        
                        if event['type'] == 'webhook.ping':
                            return ps_webhook_ping(request.headers['X-PS-Secret'])

                        elif event['type'] == 'uri.modified':
                            return ps_uri_modified(event)
                        
                        else:
                            print(json.dumps(body, indent=4))
            else:
                return Response(status=400)
    return Response(status=200)

def ps_webhook_ping(secret):
    response = Response(status=200, headers=[('X-Ps-Secret', secret)])
    return response

def ps_uri_modified(event):
    uri = event['uri']
    return Response(status=200)
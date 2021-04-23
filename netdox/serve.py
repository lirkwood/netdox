from flask import Flask, request
from flask import Response
import json
app = Flask(__name__)

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
                    if event['type'] == 'webhook.ping':
                        return ps_webhook_ping(request.headers['X-PS-Secret'])
                    else:
                        print(json.dumps(body, indent=2))
            else:
                return Response(status=400)
    return Response(status=200)

def ps_webhook_ping(secret):
    response = Response(status=200, headers=[('X-Ps-Secret', secret)])
    return response
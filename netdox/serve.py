from flask import Flask, request
from flask.wrappers import Response
import json
app = Flask(__name__)

@app.route('/')
def root():
    return Response(status=200)

@app.route('/webhooks', methods=['POST', 'GET'])
def webhooks():
    if request.content_length and request.content_length < 10**6:
        jsondata = request.get_json()
        if jsondata:
            print('POST data inboud:')
            print(json.dumps(jsondata, indent=2))
            print('Headers:')
            print(request.headers)
            try:
                ps_webhooks_ping(request.headers['X-PS-Secret'])
            except KeyError:
                pass
    return Response(status=200)

def ps_webhooks_ping(secret):
    print(f'Responding to webhook.ping with {secret}')
    return Response(status=200, headers={'X-PS-Secret': secret})


# with app.test_request_context('/webhooks', method='POST'):
#     assert request.path == '/webhooks'
#     assert request.method == 'POST'
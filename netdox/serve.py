from flask import Flask, request
from flask.wrappers import Response
app = Flask(__name__)

@app.route('/')
def root():
    return Response(status=200)

@app.route('/webhooks', methods=['POST', 'GET'])
def webhooks():
    params = request.args
    if request.content_length and request.content_length < 10**6:
        jsondata = request.get_json()
        if jsondata:
            return Response('JSON Parsed', status=200)
    return Response('No data', status=200)


# with app.test_request_context('/webhooks', method='POST'):
#     assert request.path == '/webhooks'
#     assert request.method == 'POST'
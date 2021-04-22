from flask import Flask, request
app = Flask(__name__)

@app.route('/')
def root():
    return '200 OK'

@app.route('/webhooks', methods=['POST', 'GET'])
def webhooks():
    params = request.args
    if request.content_length and request.content_length < 10**6:
        jsondata = request.get_json()
        if jsondata:
            return '200 OK json parsed'
    return '200 OK'


# with app.test_request_context('/webhooks', method='POST'):
#     assert request.path == '/webhooks'
#     assert request.method == 'POST'
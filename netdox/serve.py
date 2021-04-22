from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello_world():
    return '200 OK'

@app.route('/testing')
def test():
    return '200 OK nice :)'
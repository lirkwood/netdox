import requests
import json
import time

def token():
    try:
        stream = open('../Sources/auth_last.txt', 'r')
        token = stream.readline().strip('\n')
        last = int(stream.readline())
        stream.close()
        if (int(time.time()) - 3600) > last:   
            token = request()  # if last request was >1 hour ago token has expired
    except FileNotFoundError:
        token = request()

    return token
        

def request():
    print('Requesting new access token...')
    url = 'https://ps-doc.allette.com.au/ps/oauth/token'
    header = {
        'grant_type': 'client_credentials',
        'client_id': 'B8F2258147ADB3AD',
        'client_secret': 'fGY6Pufme2YckehTP5HEZA'
    }

    r = requests.post(url, params=header)
    token = json.loads(r.text)['access_token']
    with open('auth_last.txt', 'w') as o:
        o.write(token + '\n' + str(int(time.time())))

    return token
    


if __name__ == '__main__':
    token()

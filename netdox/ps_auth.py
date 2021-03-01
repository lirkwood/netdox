import requests, json

def token():
    try:
        with open('src/authentication.json','r') as stream:
            credentials = json.load(stream)['pageseeder']
            print('[INFO][auth.py] Requesting new access token...')
            url = 'https://ps-doc.allette.com.au/ps/oauth/token'
            header = {
                'grant_type': 'client_credentials',
                'client_id': credentials['id'],
                'client_secret': credentials['secret']
            }

            r = requests.post(url, params=header)
            token = json.loads(r.text)['access_token']

            return token

    except KeyError:
        print('[ERROR][auth.py] PageSeeder authentication failed.')
        quit()
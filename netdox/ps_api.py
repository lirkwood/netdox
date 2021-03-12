import requests, json

def auth():
    try:
        with open('src/authentication.json','r') as stream:
            credentials = json.load(stream)['pageseeder']
            ps_host = credentials["host"]
            print('[INFO][ps_api.py] Requesting new access token...')
            url = f'https://{ps_host}/ps/oauth/token'
            header = {
                'grant_type': 'client_credentials',
                'client_id': credentials['id'],
                'client_secret': credentials['secret']
            }

            r = requests.post(url, params=header)
            token = json.loads(r.text)['access_token']

            return token

    except KeyError:
        print('[ERROR][ps_api.py] PageSeeder authentication failed.')
        quit()
from bs4 import BeautifulSoup
import requests, time, json

def refresh():
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": 'application/json'
    }
    params={}
    with open('src/authentication.json','r') as stream:
        auth = json.load(stream)['secret']
        params = {
            "username": auth['username'],
            "password": auth['password'],
            "organization": "",
            "domain": "allette"
        }

    r = requests.post('https://secret.allette.com.au/webservices/SSWebservice.asmx/Authenticate', headers=headers, data=params)
    try:
        soup = BeautifulSoup(r.text, features='xml')
        with open('src/secret_token.txt','w') as stream:
            stream.write(soup.Token.string)
            stream.write(f'\n{int(time.time())}')
            return soup.Token.string
    except Exception as e:
        print('[ERROR][secret_api.py] Secret server authentication threw an exception:')
        print(e)
        print('[ERROR][secret_api.py] ****END****')
        return e

def auth():
    try:
        with open('src/secret_token.txt','r') as stream:
            token = stream.readline().strip()
            last = stream.readline()
            if int(last) > (time.time() - 7200):
                return token
            else:
                return refresh()
    except FileNotFoundError:
        return refresh()

api = 'https://secret.allette.com.au/webservices/SSWebservice.asmx'
headers = {
        'Host': 'secret.allette.com.au',
        'Content-Type': 'application/x-www-form-urlencoded',
}

def searchSecrets(term=None, field=None, exposed=True, partial=False):
    params = {}
    if term:
        params['searchTerm'] = term
    else:
        params['searchTerm'] = ''
    if field:
        params['fieldName'] = field
        params['showDeleted'] = 'false'
        params['showRestricted'] = 'true'
        if exposed:
            action = 'SearchSecretsByExposedFieldValue'
            if partial:
                params['showPartialMatches'] = 'true'
            else:
                params['showPartialMatches'] = 'false'
        else:
            action = 'SearchSecretsByFieldValue'
    else:
        action = 'SearchSecrets'
        params['includeDeleted'] = 'false'
        params['includeRestricted'] = 'true'
    
    return query(action, params)
    
# defaults = {

# }

def query(action, params={}):

    url = api +'/'+ action

    body = f'token={auth()}'
    for param in params:
        body += f'&{param}={params[param]}'

    r = requests.post(url, headers=headers, data=bytes(body, encoding='utf-8'))
    return r

if __name__ == '__main__':
    auth()
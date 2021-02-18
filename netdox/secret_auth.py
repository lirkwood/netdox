from bs4 import BeautifulSoup
from getpass import getpass
import requests, time, json

def refresh():
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": 'application/json'
    }
    params={}
    with open('src/authentication.json','r') as stream:
        auth = json.load(stream)['Secret']
        params = {
            "username": auth['Username'],
            "password": auth['Password'],
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
        print(e)
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

if __name__ == '__main__':
    refresh()
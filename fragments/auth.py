import requests
import datetime

def authenticate():
    url = ''
    header = {
        'grant_type': 'client_credentials',
        'client_id': 'B8F2258147ADB3AD',
        'client_secret': 'fGY6Pufme2YckehTP5HEZA'
    }


    r = requests.post(url)

if __name__ == '__main__':
    authenticate()
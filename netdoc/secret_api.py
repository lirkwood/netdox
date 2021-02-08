import requests
from secret_auth import auth
from bs4 import BeautifulSoup

api = 'https://secret.allette.com.au/webservices/SSWebservice.asmx'
headers = {
        'Host': 'secret.allette.com.au',
        'Content-Type': 'text/xml',
}

def searchSecrets(term):
    with open('Sources/soap.xml','r') as stream:
        soup = BeautifulSoup(stream.read(), features='xml')  #body and envelope
        soup.token.string = auth()
        soup.operation.name = 'SearchSecrets'
        soup.param.name = 'searchTerm'
        soup.searchTerm.string = term
        r = requests.post(api, headers=headers, data=bytes(str(soup), encoding='utf-8'))
        return r

if __name__ == '__main__':
    searchSecrets('test')
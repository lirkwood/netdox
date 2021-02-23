import requests
from secret_auth import auth
from bs4 import BeautifulSoup

api = 'https://secret.allette.com.au/webservices/SSWebservice.asmx'
headers = {
        'Host': 'secret.allette.com.au',
        'Content-Type': 'text/xml',
}

def searchSecrets(term=None, field=None, settings={}):
    with open('src/soap.xml','r') as stream:
        soup = BeautifulSoup(stream.read(), features='xml')  #body and envelope
        soup.token.string = auth()

        for setting in settings:
            t = soup.new_tag(setting)
            t.string = settings[setting]
            soup.param.insert_after(t)

        if not field:
            soup.operation.name = 'SearchSecrets'
        else:
            soup.operation.append(soup.new_tag('fieldName'))
            soup.operation.name = 'SearchSecretsByFieldValue'
            soup.fieldName.string = field
        soup.param.name = 'searchTerm'

        if term:
            soup.searchTerm.string = term
        r = requests.post(api, headers=headers, data=bytes(str(soup), encoding='utf-8'))
        return r

def getSecret(id, settings={}):
    with open('soap.xml','r') as stream:
        soup = BeautifulSoup(stream.read(), features='xml')  #body and envelope
        soup.token.string = auth()
        
        for setting in settings:
            t = soup.new_tag(setting)
            t.string = settings[setting]
            soup.param.insert_after(t)

        soup.operation.name = 'GetSecret'
        soup.param.name = 'secretId'
        soup.secretId.string = str(id)

        r = requests.post(api, headers=headers, data=bytes(str(soup), encoding='utf-8'))
        return r
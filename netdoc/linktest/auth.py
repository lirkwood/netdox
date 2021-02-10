from getpass import getpass
import requests
import json
import time

def token():
    try:
        stream = open('files/oauth_last.txt', 'r')
        token = stream.readline().strip('\n')
        last = int(stream.readline())
        stream.close()
        if (int(time.time()) - 3600) > last:   
            token = request()  # if last request was >1 hour ago token has expired
    except FileNotFoundError:
        token = request()

    return token
        

def request():
    try:
        with open('files/oauth_creds.txt','r') as credentials:
            print('Requesting new access token...')
            url = 'https://ps-doc.allette.com.au/ps/oauth/token'
            header = {
                'grant_type': 'client_credentials',
                'client_id': credentials.readline().strip(),
                'client_secret': credentials.readline().strip()
            }

            r = requests.post(url, params=header)
            token = json.loads(r.text)['access_token']
            with open('files/oauth_last.txt', 'w') as o:
                o.write(token + '\n' + str(int(time.time())))

            return token
    except FileNotFoundError:
        if nocreds():
            return request()
        else:
            quit()


def nocreds():
	choice = input('***ALERT***\nNo PageSeeder OAuth credentials detected. Do you wish to enter them now? (y/n): ')
	if choice == 'y':
		with open('files/oauth_creds.txt','w') as keys:
			keys.write(getpass('Enter the OAuth client ID: '))
			keys.write('\n')
			keys.write(getpass('Enter the OAuth client secret key: '))
		return True
	elif choice == 'n':
		print('Exiting...')
		return False
	else:
		print("Invalid input. Enter 'y' or 'n'.")
		return nocreds()


if __name__ == '__main__':
    token()

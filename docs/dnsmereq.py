import datetime
import urllib.request
import hmac
import hashlib
from bs4 import BeautifulSoup
import os

##################################################################################
# requests all domains from dnsme, and then all of their associated dns records. #
##################################################################################

def main():
	global response
	dmnoutput = open('../Sources/domains.xml', 'w')	#open output file
	recoutput = open('../Sources/records.xml', 'w')
	keys = open('../Sources/dnsme.txt', 'r')	#open keys file

	for line in keys:
		if line.startswith("A"):	#api key is labeled as such
			apiKey = line.split(" ")[-1].strip("\n")#remove new lines and labels
		else:
			secretKey = line.split(" ")[-1].strip("\n")
		
	genhash(secretKey, apiKey)
	print('Requesting domains')
	request("https://api.dnsmadeeasy.com/V2.0/dns/managed/")
	soup = BeautifulSoup(response, features='xml')	#make soup
	dmnoutput.write(str(soup))	#write domains.xml
	ids = []
	for id in soup.find_all('id'):
		ids.append(id.string)

	############################## Top level domains found ##############################

	soup = BeautifulSoup('', features='xml')
	root = soup.new_tag('root')
	soup.append(root)

	
	print('Requesting records')
	count = 0
	for id in ids:
		genhash(secretKey, apiKey) #refresh time, if time is >30s wrong api denies request
		url = "https://api.dnsmadeeasy.com/V2.0/dns/managed/{0}/records".format(id.string)	#grab id from tag in domans.xml and build url
		request(url)	#make request using url
		tempsoup = BeautifulSoup(response, features='xml')
		root.append(tempsoup.find('response'))
		count += 1
		if count == 149:	#150 max requests per 5 min scrolling  window
			print("Pausing for 5 MINUTES in order to not make too many requests.")
			datetime.time.sleep(300)
			count = 0

	recoutput.write(str(soup))

	dmnoutput.close()
	recoutput.close()
	keys.close()


def request(url):
	data = None
	request = urllib.request.Request(url, data, headers, method='GET')#assemble request
	global response
	response = urllib.request.urlopen(request).read().decode() #convert from http response to bytes, then to string

def genhash(s, a):
		global t
		global h
		global headers

		t = datetime.datetime.utcnow().strftime("%a, %d %b %Y %X GMT")
		h = hmac.new(bytes(s, 'utf-8'), msg=t.encode('utf-8'), digestmod=hashlib.sha1).hexdigest()
		
		headers = {	#populate header
		"x-dnsme-apiKey" : a,
		"x-dnsme-requestDate" : t,
		"x-dnsme-hmac" : h,
		"accept" : 'application/xml'
		}
	#create hash using secret key as key (as a bytes literal), the time (encoded) and sha1 mode, output as hex

if __name__ == '__main__':
	main()

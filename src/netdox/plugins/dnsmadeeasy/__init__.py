"""
Used to read and modify DNS records stored in DNSMadeEasy.
"""
import json
import os

from netdox import utils
from netdox.plugins.dnsmadeeasy.fetch import fetchDNS, fetchDomains

__stages__ = {'dns': fetchDNS}
__config__ = {'api': '', 'secret': ''}

def init() -> None:
	zones = {}
	for id, domain in fetchDomains():
		zones[domain] = id

	if not os.path.exists(utils.APPDIR+ 'plugins/dnsmadeeasy/src'):
		os.mkdir(utils.APPDIR+ 'plugins/dnsmadeeasy/src')
	with open(utils.APPDIR+ 'plugins/dnsmadeeasy/src/zones.json', 'w') as stream:
		stream.write(json.dumps(zones, indent=2))

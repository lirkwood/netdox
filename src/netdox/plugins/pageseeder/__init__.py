"""
Plugin for adding PageSeeder instance info to your network.
"""
from netdox import Network, pageseeder
from bs4 import BeautifulSoup

def licenses():
    urimap = pageseeder.urimap('website/ps-licenses', 'document')
    for uri in urimap.values():
        license_soup = BeautifulSoup(pageseeder.get_default_uriid(uri), 'xml')
        

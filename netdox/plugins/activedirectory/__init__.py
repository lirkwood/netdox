## Runner
from plugins.activedirectory.ad_api import fetchDNS as runner
stage = 'dns'

## DNS Actions
from plugins.activedirectory.ad_api import create_forward

def create_A(name: str, ip: str, zone: str):
    create_forward(name, ip, zone, 'A')

def create_CNAME(name: str, value: str, zone: str):
    create_forward(name, value, zone, 'CNAME')
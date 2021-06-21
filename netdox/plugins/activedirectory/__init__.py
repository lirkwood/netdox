"""
Used to read and modify DNS records stored in ActiveDirectory.

This plugin uses a shared storage location in order to pass information back and forth between the Netdox host and the ActiveDirectory DNS server.
"""

## Runner
from plugins.activedirectory.fetch import fetchDNS as runner
stage = 'dns'

## DNS Actions
from plugins.activedirectory.create import create_forward, create_reverse as create_PTR

def create_A(name: str, ip: str, zone: str):
    create_forward(name, ip, zone, 'A')

def create_CNAME(name: str, value: str, zone: str):
    create_forward(name, value, zone, 'CNAME')
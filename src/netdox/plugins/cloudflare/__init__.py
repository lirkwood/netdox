"""
Used to read and modify DNS records stored in CloudFlare.
"""
from netdox.plugins.cloudflare.fetch import main

__stages__ = {'dns': main}
__config__ = {'token': ''}
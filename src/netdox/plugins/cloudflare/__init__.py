"""
Used to read and modify DNS records stored in CloudFlare.
"""
from netdox.app import LifecycleStage
from netdox.plugins.cloudflare.fetch import main

__stages__ = {LifecycleStage.DNS: main}
__config__ = {'token': ''}

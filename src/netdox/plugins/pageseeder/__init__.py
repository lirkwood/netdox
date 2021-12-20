"""
Plugin for adding PageSeeder instance info to your network.
"""

from netdox.plugins.pageseeder.licenses import runner

__stages__ = {'footers': runner}
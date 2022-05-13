"""
Plugin for adding PageSeeder instance info to your network.
"""

from netdox.app import LifecycleStage
from netdox.plugins.pageseeder.licenses import runner

__stages__ = {LifecycleStage.FOOTERS: runner}
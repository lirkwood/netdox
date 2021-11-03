"""
Plugin for adding certificate information to NetworkObjects.
"""
from netdox.objs.containers import Network
from netdox.plugins.certificates.footers import analyze
import logging

logger = logging.getLogger(__name__)

def _footers(network: Network):
    for domain in network.domains:
        try:
            analyze(domain)
        except Exception:
            logger.warning('Failed to parse SSL certificate from: '+ domain.name)

__stages__ = {
    'footers': _footers
}
"""
Plugin for adding certificate information to NetworkObjects.
"""
from netdox.containers import Network
from netdox.plugins.certificates.footers import analyze
import logging

logger = logging.getLogger(__name__)

SSL_ATTR = 'ssl'
__attrs__ = {SSL_ATTR}

def _footers(network: Network):
    for domain in network.domains:
        ssl = domain.getAttr(SSL_ATTR)
        if ssl and ssl.lower().strip() in ('yes','true'):
            try:
                analyze(domain)
            except Exception:
                logger.warning('Failed to parse SSL certificate from: '+ domain.name)

__stages__ = {
    'footers': _footers
}
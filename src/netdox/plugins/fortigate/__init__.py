"""
Used to retrieve NAT information from FortiGate.
"""
from fortiosapi import FortiOSAPI
import logging

from netdox import Network
from netdox import utils, iptools
from netdox.app import LifecycleStage

logging.getLogger('fortiosapi').setLevel(logging.INFO)

def runner(network: Network) -> None:
    client = FortiOSAPI()
    client.tokenlogin(**utils.config('fortigate'))
    nat = {}

    vips = client.get('firewall/vip', '')
    for vip in vips['results']:
        for mappedIp in vip['mappedip']:
            if iptools.valid_ip(mappedIp['range']):
                nat[mappedIp['range']] = vip['extip']
                nat[vip['extip']] = mappedIp['range']
            elif iptools.valid_range(mappedIp['range']):
                raise NotImplementedError('Only 1:1 SNAT is currently implemented.')

    for ip in nat:
        network.ips[ip].translate(nat[ip], 'fortigate')

__stages__ = {
    LifecycleStage.NAT: runner
}
__config__ = {
    'apitoken': '',
    'host': ''
}

if __name__ == '__main__':
    runner(Network())
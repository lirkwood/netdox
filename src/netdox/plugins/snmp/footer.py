import logging
from pysnmp.proto.api import v2c

from netdox.containers import Network
from .objs import SNMPExplorer
from netdox.nodes import PlaceholderNode
from netdox.psml import PropertiesFragment, Property

logger = logging.getLogger(__name__)

def runner(network) -> None:
    reqPDU = v2c.GetRequestPDU()
    v2c.apiPDU.setDefaults(reqPDU)
    v2c.apiPDU.setVarBinds(reqPDU, [
        ('1.3.6.1.2.1.1.1.0', v2c.null),
    ])

    reqMsg = v2c.Message()
    v2c.apiMessage.setDefaults(reqMsg)
    v2c.apiMessage.setCommunity(reqMsg, 'public')
    v2c.apiMessage.setPDU(reqMsg, reqPDU)
    explorer = SNMPExplorer()

    resps = explorer.broadcast(reqMsg)
    for iface, varbinds in resps.items():
        ip, _ = iface
        node = PlaceholderNode(network,
            ip, ips = [ip]
        )
        node.psmlFooter.append(PropertiesFragment('snmp', [
            Property('oid', f'{oid} = {val}', 'SNMP OID')
            for oid, val in varbinds.items() if val
        ]))

if __name__ == '__main__':
    net = Network()
    runner(net)
    print([ node.psmlFooter for node in net.nodes ])
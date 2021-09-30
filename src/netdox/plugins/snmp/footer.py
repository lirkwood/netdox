import logging
from time import time
from sys import stdout

from pyasn1.codec.ber import decoder, encoder
from pysnmp.carrier.asyncore.dgram import udp
from pysnmp.carrier.asyncore.dispatch import AsyncoreDispatcher
from pysnmp.proto.api import v2c
import socket
from pprint import pprint

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(stdout))
logger.setLevel(logging.DEBUG)

def runner(network) -> None:
    reqPDU = v2c.GetRequestPDU()
    v2c.apiPDU.setDefaults(reqPDU)
    v2c.apiPDU.setVarBinds(reqPDU, [
        ('1.3.6.1.2.1.1.1.0', v2c.null),
        ('1.3.6.1.2.1.4.34.1.7', v2c.null)
    ])

    reqMsg = v2c.Message()
    v2c.apiMessage.setDefaults(reqMsg)
    v2c.apiMessage.setCommunity(reqMsg, 'public')
    v2c.apiMessage.setPDU(reqMsg, reqPDU)
    explorer = SNMPExplorer(reqMsg, txiface=('192.168.200.255', 161))
    explorer.emit()


class SNMPExplorer:
    """
    Sends an SNMP message over UDP to the an address,
    and logs the responses.
    """
    message: v2c.Message
    """Message to broadcast."""
    requestID: int
    """ID of the outbound message."""
    rxiface: tuple[str, int]
    """Interface to receive messages on. 2-tuple of IPv4 (CIDR) and port.
    Defaults to ('0.0.0.0', 161)"""
    txiface: tuple[str, int]
    """Interface to transmit messages on. 2-tuple of IPv4 (CIDR) and port.
    Defaults to ('255.255.255.255', 161)"""
    starttime: float
    """Time the request was sent."""
    maxtime: float
    """Maximum number of seconds to wait for responses."""
    maxresp: int
    """Maximum number of responses to consume."""
    dispatcher: AsyncoreDispatcher
    """Dispatcher for the messages."""
    socket: udp.UdpSocketTransport
    """Socket used for transporting the message."""

    def __init__(self, 
            message: v2c.Message, 
            maxtime: int = 5, 
            maxresp: int = 99,
            rxiface: tuple[str, int] = None,
            txiface: tuple[str, int] = None
        ) -> None:
        """
        Constructor.

        :param message: Message to broadcast.
        :type message: v2c.Message
        :param maxtime: Maximum number of seconds to wait for responses, defaults to 5
        :type maxtime: int, optional
        :param maxresp: Maximum number of responses to consume, defaults to 99
        :type maxresp: int, optional
        :param rxiface: Interface to receive messages on. 2-tuple of IPv4 (CIDR) and port.
        Defaults to (<default interface ipv4>, 161), defaults to None
        :type rxiface: tuple[str, int], optional
        :param txiface: Interface to transmit messages on. 2-tuple of IPv4 (CIDR) and port.
        Defaults to ('255.255.255.255', 161)
        :type txiface: tuple[str, int], optional
        """

        self.message = message
        self.requestID = v2c.apiPDU.getRequestID(
            v2c.apiMessage.getPDU(message)
        )

        self.maxtime = float(maxtime)
        self.maxresp = maxresp

        if rxiface:
            self.rxiface = rxiface
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            self.rxiface = (s.getsockname()[0], 161)

        self.txiface = txiface or ('255.255.255.255', 161)

        self.dispatcher = AsyncoreDispatcher()
        self.dispatcher.registerTimerCbFun(self.timer)
        self.dispatcher.registerRecvCbFun(self.recieve)


    def emit(self) -> dict[tuple[str, int], dict]:
        """
        Sends the message to *txiface* and returns the responses.
        

        :return: Dictionary mapping source interfaces to a dict of varbinds.
        :rtype: dict
        """
        self._resps = {}
        self.starttime = time()

        self.socket = udp.UdpSocketTransport().openClientMode(self.rxiface)
        self.socket.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        self.dispatcher.registerTransport(udp.domainName, self.socket)
        self.dispatcher.sendMessage(
            encoder.encode(self.message), udp.domainName, self.txiface
        )
        self.dispatcher.jobStarted(1, self.maxresp)
        
        try:
            self.dispatcher.runDispatcher()
        except TimeoutError:
            logger.debug('Timed out.')
        finally:
            self.dispatcher.closeDispatcher()
            
        return self._resps


    def timer(self, time: float) -> None:
        """
        Raises a TimeoutError when more than *self.maxtime* seconds have passed.

        :param time: Current time, in seconds since epoch.
        :type time: float
        :raises TimeoutError: When *self.maxtime* is exceeded.
        """
        if (time - self.starttime) > self.maxtime:
            raise TimeoutError

    def recieve(self, 
            dispatcher: AsyncoreDispatcher,
            domain: tuple,
            txiface: tuple[str, int],
            message: bytes
        ):
        """
        Consumes a response message.

        :param dispatcher: The dispatcher.
        :type dispatcher: AsyncioDispatcher
        :param domain: The transport domain.
        :type domain: tuple
        :param txiface: The transmit interface the message was sent from.
        :type txiface: tuple[str, int]
        :param message: The incoming response message.
        :type message: bytes
        """
        while message:
            rspMsg, message = decoder.decode(message, v2c.Message())
            rspPDU = v2c.apiMessage.getPDU(rspMsg)

            if self.requestID == v2c.apiPDU.getRequestID(rspPDU):
                logger.debug('\n\n' + str(txiface))
                outdict = self._resps[txiface] = {}

                errorStatus = v2c.apiPDU.getErrorStatus(rspPDU)
                if errorStatus:
                    logger.error(str(errorStatus))

                else:
                    for oid, value in v2c.apiPDU.getVarBinds(rspPDU):
                        logger.debug(f'{oid} = {value}')
                        if value:
                            outdict[oid] = value

                self.dispatcher.jobFinished(1)

if __name__ == '__main__':
    runner(None)
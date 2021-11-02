from __future__ import annotations

import logging
import socket
from collections import defaultdict
from dataclasses import dataclass
from time import time
from typing import Callable

from pyasn1.codec.ber import decoder, encoder
from pysnmp.carrier.asyncore.dgram import udp
from pysnmp.carrier.asyncore.dispatch import AsyncoreDispatcher
from pysnmp.proto.api import v2c

logger = logging.getLogger(__name__)

class SNMPExplorer:
    """
    Sends an SNMP message over UDP to the an address,
    and logs the responses.
    """
    rxiface: tuple[str, int]
    """Interface to receive messages on. 2-tuple of IPv4 (CIDR) and port."""
    broadcastiface: tuple[str, int]
    """Interface to broadcast messages on. 2-tuple of IPv4 (CIDR) and port.
    Defaults to ('255.255.255.255', 161)"""
    broadcastTime: float
    """Time the request was sent."""
    maxtime: float
    """Maximum number of seconds to wait for responses."""
    maxresp: int
    """Maximum number of responses to consume."""
    dispatcher: AsyncoreDispatcher
    """Dispatcher for the messages."""
    socket: udp.UdpSocketTransport
    """Socket used for transporting the message."""
    jobs: dict[tuple, Job]
    """Dictionary of active jobs. Interfaces mapped to job IDs."""
    requests: set
    """Set of IDs of requests sent by this object."""
    broadcastID: int
    """ID of initial broadcast packet."""

    def __init__(self, 
            maxtime: int = 5, 
            maxresp: int = 99,
            broadcastiface: tuple[str, int] = None
        ) -> None:
        """
        Constructor.

        :param maxtime: Maximum number of seconds to wait for responses, defaults to 5
        :type maxtime: int, optional
        :param maxresp: Maximum number of responses to consume, defaults to 99
        :type maxresp: int, optional
        :type rxiface: tuple[str, int], optional
        :param txiface: Interface to transmit messages on. 2-tuple of IPv4 (CIDR) and port.
        Defaults to ('255.255.255.255', 161)
        :type txiface: tuple[str, int], optional
        """
        self.jobs = {}
        self.requests = set()
        self.responses = defaultdict(dict)

        self.maxtime = float(maxtime)
        self.maxresp = maxresp

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        self.rxiface = (s.getsockname()[0], 161)

        self.broadcastiface = broadcastiface or ('255.255.255.255', 161)

        self.dispatcher = AsyncoreDispatcher()
        self.dispatcher.registerTimerCbFun(self.timer)
        self.dispatcher.registerRecvCbFun(self.receive)

        self.socket = udp.UdpSocketTransport().openClientMode(self.rxiface)
        self.socket.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.dispatcher.registerTransport(udp.domainName, self.socket)

    def _addJob(self, txiface: tuple[str, int], cbfun: Callable) -> int:
        """
        Adds a job to the dispatcher, with an optional callback function
        for when the job ends.

        :param txiface: Interface to associate with the job.
        :type txiface: tuple[str, int]
        :param cbfun: Object to call with *txiface* as the sole parameter once the job ends.
        :type cbfun: Callable
        :return: The ID of the job.
        :rtype: int
        """
        job = self.jobs[txiface] = Job(len(self.jobs) + 1, cbfun)
        self.dispatcher.jobStarted(job.id)
        return job.id

    def _rmJob(self, txiface: tuple[str, int]) -> int:
        """
        Removes a job from the dispatcher and executes its callback if present.

        :param txiface: Interface associated with the job.
        :type txiface: tuple[str, int]
        :return: The ID of the job.
        :rtype: int
        """
        if txiface in self.jobs:
            job = self.jobs.pop(txiface)
            if job.callback:
                job.callback(txiface)
            self.dispatcher.jobFinished(job.id)
            return job.id

    def send(self, 
            message: v2c.Message, 
            txiface: tuple[str, int], 
            cbfun: Callable = None
        ) -> int:
        """
        Sends a message and creates a job in the dispatcher.

        :param message: Message to send.
        :type message: v2c.Message
        :param txiface: Interface to send the message to.
        :type txiface: tuple[str, int]
        :param cbfun: Callback function to execute when the response is received, defaults to None
        :type cbfun: Callable, optional
        :return: The ID of the newly created job.
        :rtype: int
        """

        self.requests.add(
            v2c.apiPDU.getRequestID(v2c.apiMessage.getPDU(message))
        )
        self.dispatcher.sendMessage(
            encoder.encode(message), udp.domainName, txiface
        )
        return self._addJob(txiface, cbfun)

    def broadcast(self, 
            message: v2c.Message, 
            cbfun: Callable = None
        ) -> dict[tuple[str, int], dict]:
        """
        Broadcasts the message to *self.broadcastiface*, and logs the responses.

        :param cbfun: Callback function to execute on each response, defaults to None
        :type cbfun: Callable, optional
        :return: All the received responses for this instance.
        :rtype: A dictionary mapping 
        """
        
        self.broadcastTime = time()
        self.send(message, self.broadcastiface, cbfun)
        self.broadcastID, = self.requests
        try:
            self.dispatcher.runDispatcher()
        except TimeoutError:
            logger.debug('Timed out.')
        finally:
            self.dispatcher.closeDispatcher()
            
        return self.responses

    def timer(self, time: float) -> None:
        """
        Raises a TimeoutError when more than *self.maxtime* seconds have passed
        since last broadcast.

        :param time: Current time, in seconds since epoch.
        :type time: float
        :raises TimeoutError: When *self.maxtime* is exceeded.
        """
        if (time - self.broadcastTime) > self.maxtime:
            raise TimeoutError

    def receive(self, 
            dispatcher: AsyncoreDispatcher,
            domain: tuple,
            txiface: tuple[str, int],
            message: bytes
        ) -> None:
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
        if txiface != self.rxiface:
            logger.debug('\n\n'+ str(txiface))
            while message:
                rspMsg, message = decoder.decode(message, v2c.Message())
                rspPDU = v2c.apiMessage.getPDU(rspMsg)
                requestID = v2c.apiPDU.getRequestID(rspPDU)

                if requestID in self.requests:

                    errorStatus = v2c.apiPDU.getErrorStatus(rspPDU)
                    if errorStatus:
                        logger.error(str(errorStatus))

                    else:
                        for oid, value in v2c.apiPDU.getVarBinds(rspPDU):
                            self.responses[txiface][oid] = value if value else None

                    self._rmJob(txiface)

                else:
                    logger.debug('Unrecognised request ID '+ str(v2c.apiPDU.getRequestID(rspPDU)))

@dataclass
class Job:
    id: int
    callback: Callable

    def __init__(self, id: int, callback: Callable = None) -> None:
        self.id = id
        self.callback = callback

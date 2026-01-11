"""UDP client for MantelMount MM860."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class MantelMountResponse:
    """Response from MantelMount device."""

    command: str
    raw: str


class MantelMountProtocol(asyncio.DatagramProtocol):
    """UDP Protocol handler for MantelMount."""

    def __init__(self) -> None:
        """Initialize the protocol."""
        self.transport: asyncio.DatagramTransport | None = None
        self.response_future: asyncio.Future | None = None

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        """Handle connection made."""
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Handle received datagram."""
        if self.response_future and not self.response_future.done():
            try:
                decoded = data.decode("ascii", errors="ignore").strip()
                self.response_future.set_result(decoded)
            except Exception as e:
                self.response_future.set_exception(e)

    def error_received(self, exc: Exception) -> None:
        """Handle error."""
        _LOGGER.error("UDP error received: %s", exc)
        if self.response_future and not self.response_future.done():
            self.response_future.set_exception(exc)

    def connection_lost(self, exc: Exception | None) -> None:
        """Handle connection lost."""
        if exc and self.response_future and not self.response_future.done():
            self.response_future.set_exception(exc)


class MantelMountClient:
    """UDP client for MantelMount port 81."""

    def __init__(self, host: str, port: int = 81, timeout: float = 2.0) -> None:
        """Initialize the client."""
        self._host = host
        self._port = port
        self._timeout = timeout

    @property
    def host(self) -> str:
        """Return the host."""
        return self._host

    @property
    def port(self) -> int:
        """Return the port."""
        return self._port

    async def send(
        self,
        command: str,
        *,
        crlf: bool = False,
        read_reply: bool = True,
    ) -> MantelMountResponse:
        """
        Send a command to the MantelMount via UDP.

        The device appears to accept commands with CR or CRLF termination.
        """
        # Build the payload
        terminator = "\r\n" if crlf else "\r"
        payload = (command + terminator).encode("ascii", errors="ignore")

        loop = asyncio.get_running_loop()

        # Create UDP endpoint
        transport, protocol = await asyncio.wait_for(
            loop.create_datagram_endpoint(
                MantelMountProtocol,
                remote_addr=(self._host, self._port),
            ),
            timeout=self._timeout,
        )

        try:
            raw = ""
            if read_reply:
                # Set up response future before sending
                protocol.response_future = loop.create_future()

            # Send the command
            transport.sendto(payload)
            _LOGGER.debug("Sent UDP to %s:%s: %r", self._host, self._port, command)

            if read_reply:
                try:
                    raw = await asyncio.wait_for(
                        protocol.response_future,
                        timeout=self._timeout,
                    )
                    _LOGGER.debug("Received UDP response: %r", raw)
                except asyncio.TimeoutError:
                    _LOGGER.warning("UDP response timeout for command: %s", command)
                    raw = ""

            return MantelMountResponse(command=command, raw=raw)

        finally:
            transport.close()

from __future__ import annotations

from typing import Any

from ..core.message import Message


class Context(object):
    """What a service function and the interceptors see of one request."""

    def __init__(self, request: Message, reply: Message) -> None:
        """Create the context of a request.

        Args:
            request: the request received.
            reply: the reply being built.
        """
        self._request = request
        self._reply = reply
        self._addons: dict[str, Any] = {}

    @property
    def request(self) -> Message:
        """The request received."""
        return self._request

    @property
    def reply(self) -> Message:
        """The reply being built."""
        return self._reply

    @property
    def addons(self) -> dict[str, Any]:
        """Values that interceptors share during one request."""
        return self._addons

"""A blocking request to a service: publish it and wait for its reply."""

from __future__ import annotations

import socket
import time

from google.protobuf.message import Message as Protobuf
from pris_wire.core import Channel, Message, StatusCode, Subscription


def call(channel: Channel, request: Protobuf, topic: str, timeout: float = 5.0) -> Message:
    """Publish a request and wait for its reply.

    It consumes the channel until the reply arrives and drops any other message, so call it
    before subscribing to anything else on `channel`, such as at startup.

    Args:
        channel: the channel that publishes the request and consumes the reply.
        request: the request's content.
        topic: where the service listens.
        timeout: the most seconds to wait for the reply.

    Returns:
        The reply, whose status is OK; unpack its content with `reply.unpack`.

    Raises:
        socket.timeout: no reply within `timeout`.
        RuntimeError: the reply's status isn't OK, such as NOT_FOUND.
    """
    message = Message(content=request, reply_to=Subscription(channel))
    message.timeout = timeout
    channel.publish(message, topic=topic)
    deadline = time.time() + timeout
    while True:
        reply = channel.consume_until(deadline)
        if reply is None:
            raise socket.timeout("no reply on {} within {} s".format(topic, timeout))
        if reply.correlation_id == message.correlation_id:
            break
    if reply.status is None or reply.status.code != StatusCode.OK:
        raise RuntimeError("{}: {}".format(topic, reply.status))
    return reply

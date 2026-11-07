from __future__ import annotations

import collections
import socket
import time
import urllib.parse
from typing import TYPE_CHECKING

import amqp

from .wire.conversion import WireV1

if TYPE_CHECKING:
    from .message import Message
    from .subscription import Subscription


class Channel(object):
    """A connection to the broker, to publish messages and consume those of its subscriptions."""

    def __init__(self, uri: str = "amqp://guest:guest@localhost:5672",
                 exchange: str = "pris") -> None:
        """Connect to the broker and declare the topic exchange.

        Args:
            uri: the broker's AMQP URI; user, password, port and virtual host default to
                guest, guest, 5672 and "/".
            exchange: the topic exchange messages are published to, declared if missing.

        Raises:
            OSError: the broker can't be reached within 5 seconds.
            amqp.exceptions.AccessRefused: the broker refuses the credentials.
        """
        url = urllib.parse.urlparse(uri)

        self.connection = amqp.Connection(
            host="{}:{}".format(url.hostname or "localhost", url.port or 5672),
            userid=url.username or "guest",
            password=url.password or "guest",
            virtual_host="/" if not url.path or url.path == "/" else url.path[1:],
            connect_timeout=5.0,
        )
        self.connection.connect()

        self._channel = self.connection.channel()
        self._channel.auto_decode = False

        self._exchange = exchange
        self._channel.exchange_declare(
            exchange=self._exchange,
            type="topic",
            durable=False,
            auto_delete=False,
        )

        self.subscriptions: list[Subscription] = []
        self._prefetch = 0
        self._deliveries: collections.deque[amqp.Message] = collections.deque()

    def _on_message(self, message: amqp.Message) -> None:
        self._deliveries.append(message)

    def publish(self, message: Message, topic: str | None = None) -> None:
        """Publish a message.

        Args:
            message: the message to publish.
            topic: where to publish it; by default the message's own topic.

        Raises:
            RuntimeError: neither `topic` nor the message has a topic.
        """
        if not message.has_topic() and not topic:
            raise RuntimeError("Trying to publish message without topic")

        amqp_message = amqp.Message(
            body=message.body,
            channel=self._channel,
            **WireV1.to_amqp_properties(message),
        )

        self._channel.basic_publish(
            amqp_message,
            exchange=self._exchange,
            routing_key=message.topic if topic is None else topic,
            immediate=False,
            mandatory=False,
        )

    def consume(self, timeout: float | None = None) -> Message:
        """Wait for the next message of this channel's subscriptions.

        Args:
            timeout: the most seconds to wait, 0 to not wait; by default, forever.

        Returns:
            The oldest message received.

        Raises:
            socket.timeout: no message arrived within `timeout`.
        """
        if timeout is not None:
            assert timeout >= 0.0

        while not self._deliveries:
            self.connection.drain_events(timeout)
        return WireV1.from_amqp_message(self._deliveries.popleft())

    def consume_for(self, timeout: float) -> Message | None:
        """Wait at most `timeout` seconds for the next message.

        Args:
            timeout: the most seconds to wait; a negative value doesn't wait.

        Returns:
            The oldest message received, or None if none arrived in time.
        """
        try:
            return self.consume(timeout=max(0.0, timeout))
        except socket.timeout:
            return None

    def consume_until(self, deadline: float) -> Message | None:
        """Wait until `deadline` for the next message.

        Args:
            deadline: seconds since the epoch, the clock of time.time() and Message.created_at;
                a deadline in the past doesn't wait.

        Returns:
            The oldest message received, or None if none arrived before the deadline.
        """
        return self.consume_for(deadline - time.time())

    def consume_ready(self) -> list[Message]:
        """Return every message already received, without waiting.

        Returns:
            The messages, oldest first; empty if there is none.
        """
        messages: list[Message] = []
        while True:
            message = self.consume_for(0.0)
            if message is None:
                return messages
            messages.append(message)

    def ack(self, message: Message) -> None:
        """Acknowledge a message of a subscription with manual_ack: the broker forgets it.

        Args:
            message: a message received by this channel.

        Raises:
            ValueError: the message has no delivery tag.
        """
        self._channel.basic_ack(delivery_tag=self._delivery_tag(message))

    def reject(self, message: Message, requeue: bool = False) -> None:
        """Reject a message of a subscription with manual_ack.

        Args:
            message: a message received by this channel.
            requeue: put it back in the queue instead of dropping (or dead-lettering) it.

        Raises:
            ValueError: the message has no delivery tag.
        """
        self._channel.basic_reject(delivery_tag=self._delivery_tag(message), requeue=requeue)

    @staticmethod
    def _delivery_tag(message: Message) -> int:
        if message.delivery_tag is None:
            raise ValueError("message has no delivery tag: was it received by this channel?")
        return message.delivery_tag

    def close(self) -> None:
        """Close the connection to the broker."""
        self.connection.close()

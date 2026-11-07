from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .utils import consumer_id

if TYPE_CHECKING:
    from .channel import Channel


class Subscription(object):
    """A queue that receives the messages of the topics it subscribes to."""

    def __init__(self, channel: Channel, name: str | None = None,
                 arguments: dict[str, Any] | None = None, prefetch: int | None = None,
                 manual_ack: bool = False) -> None:
        """Declare a queue bound to its own name and consume it on `channel`.

        The queue is deleted once its last consumer is gone.

        Args:
            channel: the channel that receives the messages.
            name: the queue's name; without one, the queue is private to this connection, e.g.
                for RPC replies. Several consumers of one named queue, such as a service's
                replicas, split its messages.
            arguments: queue arguments for the broker, e.g.
                {"x-max-length": 1, "x-overflow": "drop-head"} to keep only the newest message.
            prefetch: the most unacknowledged messages the broker sends at once; needs
                `manual_ack`.
            manual_ack: settle every message with Channel.ack or Channel.reject; otherwise the
                broker forgets a message once it is sent.

        Raises:
            ValueError: `prefetch` is given without `manual_ack`, or isn't a positive integer.
            amqp.exceptions.PreconditionFailed: the queue exists with other arguments.
        """
        if prefetch is not None and not manual_ack:
            raise ValueError("prefetch needs manual_ack: without acks the broker ignores it")
        if prefetch is not None and (not isinstance(prefetch, int) or prefetch < 1):
            raise ValueError("prefetch must be a positive integer, got {!r}".format(prefetch))

        self._id = consumer_id()
        self._name = self._id if name is None else name
        self._topics: set[str] = set()
        self._manual_ack = manual_ack

        self._channel = channel._channel
        self._exchange = channel._exchange
        private = name is None

        self._channel.queue_declare(
            queue=self._name,
            passive=False,
            durable=not private,
            exclusive=private,
            auto_delete=True,
            arguments=dict(arguments or {}),
        )

        self._channel.queue_bind(
            queue=self._name,
            exchange=self._exchange,
            routing_key=self._name,
        )

        prefetch_count = prefetch or 0
        if getattr(channel, "_prefetch", 0) != prefetch_count:
            self._channel.basic_qos(prefetch_size=0, prefetch_count=prefetch_count,
                                    a_global=False)
            channel._prefetch = prefetch_count

        self._channel.basic_consume(
            queue=self._name,
            callback=channel._on_message,
            consumer_tag=self._id,
            no_local=False,
            no_ack=not manual_ack,
            exclusive=False,
        )

    def subscribe(self, topic: str) -> None:
        """Receive the messages published to a topic.

        Args:
            topic: the topic, which may use the AMQP wildcards * and #.
        """
        self._channel.queue_bind(
            queue=self._name,
            exchange=self._exchange,
            routing_key=topic,
        )
        self._topics.add(topic)

    def unsubscribe(self, topic: str) -> None:
        """Stop receiving the messages of a topic.

        Args:
            topic: a topic subscribed to.

        Raises:
            KeyError: the subscription isn't subscribed to `topic`.
        """
        self._channel.queue_unbind(
            queue=self._name,
            exchange=self._exchange,
            routing_key=topic,
        )
        self._topics.remove(topic)

    @property
    def id(self) -> str:
        """The consumer id, set as the subscription_id of every message received."""
        return self._id

    @property
    def name(self) -> str:
        """The queue's name: the given one, or the id for a private queue."""
        return self._name

    @property
    def manual_ack(self) -> bool:
        """Whether messages must be settled with Channel.ack or Channel.reject."""
        return self._manual_ack

    @property
    def topics(self) -> set[str]:
        """The topics subscribed to."""
        return self._topics

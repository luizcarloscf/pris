"""The service: follow the binding events and publish the consumers of each topic."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from opentelemetry import trace
from opentelemetry.instrumentation.pris_wire import extract
from opentelemetry.trace import SpanKind
from pris_msgs.common_pb2 import ConsumerList
from pris_wire.core import Channel, Logger, Message, Subscription


class BrokerEvents(object):
    """Keeps the consumers of each topic and publishes them whenever they change."""

    log = Logger("BrokerEvents")

    def __init__(self, channel: Channel, topic: str = "BrokerEvents.Consumers",
                 exchange: str = "pris") -> None:
        """Subscribe to the binding events on the shared queue `BrokerEvents`.

        Subscribe before querying the bindings with `load`, so that no binding falls between them.

        Args:
            channel: the channel that consumes the events and publishes the consumers.
            topic: where the consumers are published.
            exchange: the exchange whose bindings are the consumers.
        """
        self.channel = channel
        self.topic = topic
        self.exchange = exchange
        self.consumers = ConsumerList()
        self.subscription = Subscription(channel, name="BrokerEvents")
        self.subscription.subscribe("binding.*")

    def load(self, bindings: Iterable[dict[str, Any]]) -> None:
        """Start from the bindings of the management API.

        Args:
            bindings: as `management.fetch_bindings` returns them.
        """
        self.consumers = self.consumers_from_bindings(bindings, self.exchange)

    def run(self) -> None:
        """Handle the events until the process stops."""
        while True:
            self.handle(self.channel.consume())

    def handle(self, message: Message) -> None:
        """Apply one event and, if it changed the consumers, publish them.

        Args:
            message: a `binding.*` event.
        """
        with trace.get_tracer(__name__).start_as_current_span(
            "process {}".format(message.topic),
            context=extract(message),
            kind=SpanKind.CONSUMER,
            attributes={
                "messaging.system": "rabbitmq",
                "messaging.operation.type": "process",
                "messaging.operation.name": "process",
                "messaging.destination.name": "{}:{}".format(self.exchange, message.topic),
            },
        ) as span:
            if not self.apply_event(self.consumers, message, self.exchange):
                span.set_attribute("pris.broker_events.ignored", True)
                return
            topic = message.metadata["routing_key"]
            queue = message.metadata["destination_name"]
            span.set_attributes({
                "pris.broker_events.binding.topic": topic,
                "pris.broker_events.binding.queue": queue,
            })
            self.log.info("event='{}' topic='{}' queue='{}'",
                          (message.topic or "").split(".")[-1], topic, queue)
            self.channel.publish(Message(content=self.consumers), topic=self.topic)

    @staticmethod
    def consumers_from_bindings(bindings: Iterable[dict[str, Any]],
                                exchange: str = "pris") -> ConsumerList:
        """Build the consumers of each topic from the management API's bindings.

        Args:
            bindings: the bindings, as `GET /api/bindings` returns them.
            exchange: the exchange whose bindings are the consumers.

        Returns:
            The queues bound to each routing key of `exchange`; other bindings are ignored.
        """
        consumers = ConsumerList()
        for binding in bindings:
            if binding["destination_type"] == "queue" and binding["source"] == exchange:
                consumers.info[binding["routing_key"]].consumers.append(binding["destination"])
        return consumers

    @staticmethod
    def apply_event(consumers: ConsumerList, message: Message, exchange: str = "pris") -> bool:
        """Update the consumers with a `binding.created` or `binding.deleted` event.

        A binding created between the subscription to the events and the initial query comes
        twice, and is kept once.

        Args:
            consumers: the list to update.
            message: the event, as the broker's event exchange publishes it.
            exchange: the exchange whose bindings are the consumers.

        Returns:
            False, leaving `consumers` untouched, for an event that isn't about a queue bound to
            `exchange`.
        """
        metadata = message.metadata
        if metadata.get("destination_kind") != "queue" or metadata.get("source_name") != exchange:
            return False

        event = (message.topic or "").split(".")[-1]
        topic = metadata["routing_key"]
        queue = metadata["destination_name"]

        if event == "created":
            if queue not in consumers.info[topic].consumers:
                consumers.info[topic].consumers.append(queue)
        elif event == "deleted" and topic in consumers.info:
            if queue in consumers.info[topic].consumers:
                consumers.info[topic].consumers.remove(queue)
            if len(consumers.info[topic].consumers) == 0:
                del consumers.info[topic]
        return True

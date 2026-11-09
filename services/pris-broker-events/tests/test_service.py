from pathlib import Path

import pytest
from opentelemetry.trace import SpanKind
from pris_msgs.common_pb2 import ConsumerList
from pris_msgs.utils.io import load
from pris_wire.core import Message, Subscription

from pris_broker_events.conf.options_pb2 import BrokerEventsOptions
from pris_broker_events.management import fetch_bindings
from pris_broker_events.service import BrokerEvents

DEFAULT_OPTIONS = Path(__file__).parents[1] / "etc" / "conf" / "options.json"


@pytest.fixture
def service(channel, management_uri):
    service = BrokerEvents(channel)
    service.load(fetch_bindings(management_uri, timeout=5.0))
    return service


def handle_until(service, condition):
    for _ in range(50):
        service.handle(service.channel.consume(timeout=2.0))
        if condition(service.consumers):
            return
    raise AssertionError("the consumers never matched")


def test_default_options():
    options = load(str(DEFAULT_OPTIONS), BrokerEventsOptions)

    assert options.broker_uri == "amqp://guest:guest@rabbitmq.pris"
    assert options.broker_management_api.uri == "http://guest:guest@rabbitmq.pris"
    assert options.telemetry.otlp_endpoint == "http://otel-collector.pris:4318"


def test_starts_from_the_existing_bindings(service):
    assert list(service.consumers.info["binding.*"].consumers) == ["BrokerEvents"]


def test_a_new_subscription_is_published(service, connect, topic):
    listener = connect()
    Subscription(listener).subscribe(service.topic)
    Subscription(connect(), name=topic)

    handle_until(service, lambda consumers: topic in consumers.info)

    while True:
        consumers = listener.consume(timeout=2.0).unpack(ConsumerList)
        if topic in consumers.info:
            break
    assert list(consumers.info[topic].consumers) == [topic]


def test_an_unsubscribed_topic_is_removed(service, connect, topic):
    subscription = Subscription(connect())
    subscription.subscribe(topic)
    handle_until(service, lambda consumers: topic in consumers.info)

    subscription.unsubscribe(topic)

    handle_until(service, lambda consumers: topic not in consumers.info)


def test_the_process_span_wraps_the_publish(service, connect, topic, spans):
    Subscription(connect(), name=topic)

    handle_until(service, lambda consumers: topic in consumers.info)

    spans_by_id = {span.context.span_id: span for span in spans.get_finished_spans()}
    process = next(span for span in spans_by_id.values()
                   if span.attributes.get("pris.broker_events.binding.queue") == topic)
    assert process.kind == SpanKind.CONSUMER
    assert process.name == "process binding.created"
    publish = next(span for span in spans_by_id.values()
                   if span.parent is not None and span.parent.span_id == process.context.span_id)
    assert publish.name == "publish BrokerEvents.Consumers"


def test_an_ignored_event_publishes_nothing(service, spans):
    message = Message()
    message.topic = "binding.created"
    message.metadata = {"source_name": "pris", "destination_kind": "exchange"}

    service.handle(message)

    (process,) = spans.get_finished_spans()
    assert process.attributes["pris.broker_events.ignored"] is True

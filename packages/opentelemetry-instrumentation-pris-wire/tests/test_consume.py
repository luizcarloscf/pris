import socket
import time

import pytest
from pris_wire.core import Message, Status, StatusCode, Subscription
from opentelemetry.instrumentation.pris_wire import extract
from opentelemetry.trace import SpanKind, StatusCode as SpanStatusCode


def server(channel):
    host, port = channel.connection.host.rsplit(":", 1)
    return {"server.address": host, "server.port": int(port)}


def test_receive_span_is_child_of_producer_without_current_span(instrument, telemetry, channel,
                                                                topic):
    instrument()
    message = Message(content=b"frame")
    message.correlation_id = 0x1F

    channel.publish(message, topic=topic)
    received = channel.consume(timeout=1.0)

    assert received.body == b"frame"
    publish, receive = telemetry.spans()
    assert receive.name == "receive " + topic
    assert receive.kind == SpanKind.CLIENT
    assert dict(receive.attributes) == {
        "messaging.system": "rabbitmq",
        "messaging.operation.type": "receive",
        "messaging.operation.name": "receive",
        "messaging.destination.name": "pris:" + topic,
        "messaging.rabbitmq.destination.routing_key": topic,
        "messaging.message.conversation_id": "1F",
        "messaging.message.body.size": 5,
        **server(channel),
    }
    (link,) = receive.links
    assert link.context.span_id == publish.context.span_id
    assert receive.parent.span_id == publish.context.span_id
    assert receive.context.trace_id == publish.context.trace_id


def test_receive_span_starts_when_the_message_arrives(instrument, telemetry, channel, topic,
                                                      monkeypatch):
    instrument()
    channel.publish(Message(content=b"frame"), topic=topic)
    drain = channel.connection.drain_events

    def slow_drain(timeout=None):
        time.sleep(0.2)
        return drain(timeout)

    monkeypatch.setattr(channel.connection, "drain_events", slow_drain)
    channel.consume(timeout=1.0)

    publish, receive = telemetry.spans()
    assert receive.start_time >= publish.end_time + 200_000_000
    assert receive.end_time - receive.start_time < 50_000_000


def test_receive_span_is_child_of_current_span(instrument, telemetry, channel, topic):
    instrument()
    channel.publish(Message(content=b"frame"), topic=topic)

    tracer = telemetry.tracer_provider.get_tracer("test")
    with tracer.start_as_current_span("loop"):
        channel.consume(timeout=1.0)

    publish, receive, loop = telemetry.spans()
    assert receive.parent.span_id == loop.context.span_id
    (link,) = receive.links
    assert link.context.span_id == publish.context.span_id


def test_receive_span_for_message_delivered_before_consume(instrument, telemetry, channel, topic):
    instrument()
    channel.publish(Message(content=b"frame"), topic=topic)
    channel.connection.drain_events(timeout=1.0)

    received = channel.consume(timeout=0.0)

    assert received.body == b"frame"
    publish, receive = telemetry.spans()
    (link,) = receive.links
    assert link.context.span_id == publish.context.span_id


def test_consume_variants_are_traced(instrument, telemetry, channel, topic):
    instrument()
    for n in range(3):
        channel.publish(Message(content=str(n).encode()), topic=topic)

    assert channel.consume_for(1.0).body == b"0"
    assert channel.consume_until(time.time() + 1.0).body == b"1"
    ready = []
    while not ready:
        ready = channel.consume_ready()
    assert [message.body for message in ready] == [b"2"]

    receives = [span for span in telemetry.spans() if span.kind == SpanKind.CLIENT]
    assert len(receives) == 3


def test_extract_gives_receive_span_as_parent(instrument, telemetry, channel, topic):
    instrument()
    channel.publish(Message(), topic=topic)
    received = channel.consume(timeout=1.0)

    tracer = telemetry.tracer_provider.get_tracer("test")
    with tracer.start_as_current_span("handle", context=extract(received)):
        pass

    publish, receive, handle = telemetry.spans()
    assert handle.parent.span_id == receive.context.span_id
    assert handle.context.trace_id == publish.context.trace_id
    assert "{:016x}".format(receive.context.span_id) in received.metadata["traceparent"]


def test_receive_reply_has_bounded_name(instrument, telemetry, channel):
    instrument()
    reply_queue = Subscription(channel).name
    reply = Message()
    reply.status = Status(StatusCode.OK)

    channel.publish(reply, topic=reply_queue)
    channel.consume(timeout=1.0)

    receive = telemetry.spans()[-1]
    assert receive.name == "receive (reply)"
    assert receive.attributes["messaging.destination.temporary"] is True
    assert receive.attributes["messaging.rabbitmq.destination.routing_key"] == reply_queue
    (consumed,) = telemetry.metrics()["messaging.client.consumed.messages"]
    assert consumed.attributes["messaging.destination.name"] == "pris:(reply)"


def test_receive_metrics(instrument, telemetry, channel, topic):
    instrument()
    for _ in range(2):
        channel.publish(Message(), topic=topic)
        channel.consume(timeout=1.0)

    metrics = telemetry.metrics()
    (consumed,) = metrics["messaging.client.consumed.messages"]
    assert consumed.value == 2
    durations = {p.attributes["messaging.operation.type"]: p.count
                 for p in metrics["messaging.client.operation.duration"]}
    assert durations == {"send": 2, "receive": 2}


def test_timeout_is_not_traced(instrument, telemetry, channel):
    instrument()

    with pytest.raises(socket.timeout):
        channel.consume(timeout=0.0)

    assert telemetry.spans() == ()
    assert "messaging.client.operation.duration" not in telemetry.metrics()


def test_receive_error(instrument, telemetry, channel, monkeypatch):
    def broken(timeout=None):
        raise ConnectionResetError("broker gone")

    instrument()
    monkeypatch.setattr(channel.connection, "drain_events", broken)

    with pytest.raises(ConnectionResetError):
        channel.consume()

    (span,) = telemetry.spans()
    assert span.name == "receive"
    assert span.status.status_code == SpanStatusCode.ERROR
    assert span.attributes["error.type"] == "ConnectionResetError"
    (duration,) = telemetry.metrics()["messaging.client.operation.duration"]
    assert duration.attributes["error.type"] == "ConnectionResetError"
    assert "messaging.client.consumed.messages" not in telemetry.metrics()


def test_consume_hook(instrument, telemetry, channel, topic):
    calls = []

    def hook(span, message):
        calls.append((span.name, message.body))
        span.set_attribute("custom", "yes")

    instrument(consume_hook=hook)
    channel.publish(Message(content=b"x"), topic=topic)
    channel.consume(timeout=1.0)

    assert calls == [("receive " + topic, b"x")]
    assert telemetry.spans()[-1].attributes["custom"] == "yes"


def test_failing_consume_hook_does_not_lose_message(instrument, telemetry, channel, topic):
    def hook(span, message):
        raise ValueError("bug in hook")

    instrument(consume_hook=hook)
    channel.publish(Message(content=b"x"), topic=topic)

    assert channel.consume(timeout=1.0).body == b"x"

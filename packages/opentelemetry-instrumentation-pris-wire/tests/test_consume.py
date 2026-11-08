import socket
import time

import pytest
from pris_wire.core import Message, Status, StatusCode
from opentelemetry.instrumentation.pris_wire import extract
from opentelemetry.trace import SpanKind, StatusCode as SpanStatusCode


def published_then_consumed(channel, message, topic):
    channel.publish(message, topic=topic)
    channel.connection.loopback()
    return channel.consume(timeout=1.0)


def test_receive_span_is_child_of_producer_without_current_span(instrument, telemetry, channel):
    instrument()
    message = Message(content=b"frame")
    message.correlation_id = 0x1F

    received = published_then_consumed(channel, message, "Camera.0.Frame")

    assert received.body == b"frame"
    publish, receive = telemetry.spans()
    assert receive.name == "receive Camera.0.Frame"
    assert receive.kind == SpanKind.CLIENT
    assert dict(receive.attributes) == {
        "messaging.system": "rabbitmq",
        "messaging.operation.type": "receive",
        "messaging.operation.name": "receive",
        "messaging.destination.name": "pris:Camera.0.Frame",
        "messaging.rabbitmq.destination.routing_key": "Camera.0.Frame",
        "messaging.message.conversation_id": "1F",
        "messaging.message.body.size": 5,
        "server.address": "broker.local",
        "server.port": 5672,
    }
    (link,) = receive.links
    assert link.context.span_id == publish.context.span_id
    assert receive.parent.span_id == publish.context.span_id
    assert receive.context.trace_id == publish.context.trace_id


def test_receive_span_starts_when_the_message_arrives(instrument, telemetry, channel, monkeypatch):
    instrument()
    channel.publish(Message(content=b"frame"), topic="Camera.0.Frame")
    channel.connection.loopback()
    drain = channel.connection.drain_events

    def slow_drain(timeout=None):
        time.sleep(0.2)
        return drain(timeout)

    monkeypatch.setattr(channel.connection, "drain_events", slow_drain)
    channel.consume(timeout=1.0)

    publish, receive = telemetry.spans()
    assert receive.start_time >= publish.start_time + 200_000_000
    assert receive.end_time - receive.start_time < 50_000_000


def test_receive_span_is_child_of_current_span(instrument, telemetry, channel):
    instrument()
    channel.publish(Message(content=b"frame"), topic="Camera.0.Frame")
    channel.connection.loopback()

    tracer = telemetry.tracer_provider.get_tracer("test")
    with tracer.start_as_current_span("loop"):
        channel.consume(timeout=1.0)

    publish, receive, loop = telemetry.spans()
    assert receive.parent.span_id == loop.context.span_id
    (link,) = receive.links
    assert link.context.span_id == publish.context.span_id


def test_receive_span_for_message_delivered_before_consume(instrument, telemetry, channel):
    instrument()
    channel.publish(Message(content=b"frame"), topic="Camera.0.Frame")
    channel.connection.loopback()
    channel.connection.drain_events(timeout=0)

    received = channel.consume(timeout=0.0)

    assert received.body == b"frame"
    publish, receive = telemetry.spans()
    assert receive.name == "receive Camera.0.Frame"
    (link,) = receive.links
    assert link.context.span_id == publish.context.span_id


def test_consume_variants_are_traced(instrument, telemetry, channel):
    instrument()
    for topic in ("Camera.0.Frame", "Camera.1.Frame", "Camera.2.Frame"):
        channel.publish(Message(content=b"frame"), topic=topic)
    channel.connection.loopback()

    assert channel.consume_for(1.0).topic == "Camera.0.Frame"
    assert channel.consume_until(0.0).topic == "Camera.1.Frame"
    assert [message.topic for message in channel.consume_ready()] == ["Camera.2.Frame"]
    assert channel.consume_for(0.0) is None

    receives = [span.name for span in telemetry.spans() if span.name.startswith("receive")]
    assert receives == ["receive Camera.0.Frame", "receive Camera.1.Frame",
                        "receive Camera.2.Frame"]


def test_extract_gives_receive_span_as_parent(instrument, telemetry, channel):
    instrument()
    received = published_then_consumed(channel, Message(), "A")

    tracer = telemetry.tracer_provider.get_tracer("test")
    with tracer.start_as_current_span("handle", context=extract(received)):
        pass

    publish, receive, handle = telemetry.spans()
    assert handle.parent.span_id == receive.context.span_id
    assert handle.context.trace_id == publish.context.trace_id
    assert "{:016x}".format(receive.context.span_id) in received.metadata["traceparent"]


def test_receive_reply_has_bounded_name(instrument, telemetry, channel):
    instrument()
    reply = Message()
    reply.status = Status(StatusCode.OK)

    published_then_consumed(channel, reply, "host/1A2B3C")

    receive = telemetry.spans()[-1]
    assert receive.name == "receive (reply)"
    assert receive.attributes["messaging.destination.temporary"] is True
    assert receive.attributes["messaging.rabbitmq.destination.routing_key"] == "host/1A2B3C"
    (consumed,) = telemetry.metrics()["messaging.client.consumed.messages"]
    assert consumed.attributes["messaging.destination.name"] == "pris:(reply)"


def test_receive_metrics(instrument, telemetry, channel):
    instrument()
    published_then_consumed(channel, Message(), "A")
    published_then_consumed(channel, Message(), "A")

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


def test_receive_error(instrument, telemetry, channel):
    instrument()
    channel.connection.error = ConnectionResetError("broker gone")

    with pytest.raises(ConnectionResetError):
        channel.consume()

    (span,) = telemetry.spans()
    assert span.name == "receive"
    assert span.status.status_code == SpanStatusCode.ERROR
    assert span.attributes["error.type"] == "ConnectionResetError"
    (duration,) = telemetry.metrics()["messaging.client.operation.duration"]
    assert duration.attributes["error.type"] == "ConnectionResetError"
    assert "messaging.client.consumed.messages" not in telemetry.metrics()


def test_consume_hook(instrument, telemetry, channel):
    calls = []

    def hook(span, message):
        calls.append((span.name, message.body))
        span.set_attribute("custom", "yes")

    instrument(consume_hook=hook)
    published_then_consumed(channel, Message(content=b"x"), "A")

    assert calls == [("receive A", b"x")]
    assert telemetry.spans()[-1].attributes["custom"] == "yes"


def test_failing_consume_hook_does_not_lose_message(instrument, telemetry, channel):
    def hook(span, message):
        raise ValueError("bug in hook")

    instrument(consume_hook=hook)
    received = published_then_consumed(channel, Message(content=b"x"), "A")

    assert received.body == b"x"

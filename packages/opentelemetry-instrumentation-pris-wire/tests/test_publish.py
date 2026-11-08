import pytest
from pris_wire.core import Message, Status, StatusCode, Subscription
from opentelemetry.instrumentation.pris_wire import PrisWireInstrumentor
from opentelemetry.trace import SpanKind, StatusCode as SpanStatusCode


def server(channel):
    host, port = channel.connection.host.rsplit(":", 1)
    return {"server.address": host, "server.port": int(port)}


def test_publish_span(instrument, telemetry, channel, topic):
    instrument()
    message = Message(content=b"hello")
    message.correlation_id = 0xABC

    channel.publish(message, topic=topic)

    (span,) = telemetry.spans()
    assert span.name == "publish " + topic
    assert span.kind == SpanKind.PRODUCER
    assert dict(span.attributes) == {
        "messaging.system": "rabbitmq",
        "messaging.operation.type": "send",
        "messaging.operation.name": "publish",
        "messaging.destination.name": "pris:" + topic,
        "messaging.rabbitmq.destination.routing_key": topic,
        "messaging.message.conversation_id": "ABC",
        "messaging.message.body.size": 5,
        **server(channel),
    }


def test_publish_injects_context_into_headers(instrument, telemetry, channel, topic):
    instrument()
    message = Message()
    message.metadata = {"x-custom": "kept"}

    channel.publish(message, topic=topic)
    received = channel.consume(timeout=1.0)

    publish = telemetry.spans()[0]
    assert received.metadata["x-custom"] == "kept"
    assert "{:032x}".format(publish.context.trace_id) in received.metadata["traceparent"]


def test_publish_uses_message_topic(instrument, telemetry, channel, topic):
    instrument()
    message = Message()
    message.topic = topic

    channel.publish(message)

    assert telemetry.spans()[0].name == "publish " + topic
    assert channel.consume(timeout=1.0).topic == topic


def test_publish_reply_has_bounded_name(instrument, telemetry, channel):
    instrument()
    reply_queue = Subscription(channel).name
    reply = Message()
    reply.topic = reply_queue
    reply.status = Status(StatusCode.OK)

    channel.publish(reply)

    (span,) = telemetry.spans()
    assert span.name == "publish (reply)"
    assert span.attributes["messaging.destination.name"] == "pris:(reply)"
    assert span.attributes["messaging.destination.temporary"] is True
    assert span.attributes["messaging.rabbitmq.destination.routing_key"] == reply_queue
    for point in telemetry.metrics()["messaging.client.sent.messages"]:
        assert reply_queue not in point.attributes.values()


def test_publish_metrics(instrument, telemetry, channel, topic):
    instrument()
    channel.publish(Message(), topic=topic)
    channel.publish(Message(), topic=topic)

    metrics = telemetry.metrics()
    (sent,) = metrics["messaging.client.sent.messages"]
    assert sent.value == 2
    assert sent.attributes["messaging.destination.name"] == "pris:" + topic
    (duration,) = metrics["messaging.client.operation.duration"]
    assert duration.count == 2
    assert list(duration.explicit_bounds)[:3] == [0.005, 0.01, 0.025]


def test_publish_error(instrument, telemetry, channel, topic, monkeypatch):
    def broken(*args, **kwargs):
        raise ConnectionError("broker gone")

    instrument()
    monkeypatch.setattr(channel._channel, "basic_publish", broken)

    with pytest.raises(ConnectionError):
        channel.publish(Message(), topic=topic)

    (span,) = telemetry.spans()
    assert span.status.status_code == SpanStatusCode.ERROR
    assert span.attributes["error.type"] == "ConnectionError"
    (sent,) = telemetry.metrics()["messaging.client.sent.messages"]
    assert sent.attributes["error.type"] == "ConnectionError"


def test_publish_without_topic_is_not_traced(instrument, telemetry, channel):
    instrument()
    with pytest.raises(RuntimeError):
        channel.publish(Message())
    assert telemetry.spans() == ()


def test_publish_hook(instrument, telemetry, channel, topic):
    calls = []

    def hook(span, message):
        calls.append((span.name, message))
        span.set_attribute("custom", "yes")

    instrument(publish_hook=hook)
    message = Message()
    channel.publish(message, topic=topic)

    assert calls == [("publish " + topic, message)]
    assert telemetry.spans()[0].attributes["custom"] == "yes"


def test_failing_hook_does_not_break_publish(instrument, telemetry, channel, topic):
    def hook(span, message):
        raise ValueError("bug in hook")

    instrument(publish_hook=hook)
    channel.publish(Message(content=b"x"), topic=topic)

    assert channel.consume(timeout=1.0).body == b"x"
    assert len(telemetry.spans()) == 2


def test_uninstrument(instrument, telemetry, channel, topic):
    instrument()
    PrisWireInstrumentor().uninstrument()

    channel.publish(Message(content=b"x"), topic=topic)

    assert channel.consume(timeout=1.0).body == b"x"
    assert telemetry.spans() == ()

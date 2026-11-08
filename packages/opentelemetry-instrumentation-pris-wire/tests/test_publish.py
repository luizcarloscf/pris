import pytest
from pris_wire.core import Message, Status, StatusCode
from opentelemetry import trace
from opentelemetry.instrumentation.pris_wire import PrisWireInstrumentor, extract
from opentelemetry.trace import SpanKind, StatusCode as SpanStatusCode


def test_publish_span(instrument, telemetry, channel):
    instrument()
    message = Message(content=b"hello")
    message.correlation_id = 0xABC

    channel.publish(message, topic="Camera.0.Frame")

    (span,) = telemetry.spans()
    assert span.name == "publish Camera.0.Frame"
    assert span.kind == SpanKind.PRODUCER
    assert dict(span.attributes) == {
        "messaging.system": "rabbitmq",
        "messaging.operation.type": "send",
        "messaging.operation.name": "publish",
        "messaging.destination.name": "pris:Camera.0.Frame",
        "messaging.rabbitmq.destination.routing_key": "Camera.0.Frame",
        "messaging.message.conversation_id": "ABC",
        "messaging.message.body.size": 5,
        "server.address": "broker.local",
        "server.port": 5672,
    }


def test_publish_injects_context_into_headers(instrument, telemetry, channel):
    instrument()
    message = Message()
    message.metadata = {"x-custom": "kept"}

    channel.publish(message, topic="Some.Topic")

    (span,) = telemetry.spans()
    (sent,) = channel._channel.published
    headers = sent.message.properties["application_headers"]
    assert headers["x-custom"] == "kept"
    assert "{:032x}".format(span.context.trace_id) in headers["traceparent"]

    received = extract(message)
    assert trace.get_current_span(received).get_span_context().span_id == span.context.span_id


def test_publish_uses_message_topic(instrument, telemetry, channel):
    instrument()
    message = Message()
    message.topic = "From.Message"

    channel.publish(message)

    assert telemetry.spans()[0].name == "publish From.Message"
    assert channel._channel.published[0].routing_key == "From.Message"


def test_publish_reply_has_bounded_name(instrument, telemetry, channel):
    instrument()
    reply = Message()
    reply.topic = "host/1A2B3C"
    reply.status = Status(StatusCode.OK)

    channel.publish(reply)

    (span,) = telemetry.spans()
    assert span.name == "publish (reply)"
    assert span.attributes["messaging.destination.name"] == "pris:(reply)"
    assert span.attributes["messaging.destination.temporary"] is True
    assert span.attributes["messaging.rabbitmq.destination.routing_key"] == "host/1A2B3C"
    for point in telemetry.metrics()["messaging.client.sent.messages"]:
        assert "host/1A2B3C" not in point.attributes.values()


def test_publish_metrics(instrument, telemetry, channel):
    instrument()
    channel.publish(Message(), topic="A")
    channel.publish(Message(), topic="A")

    metrics = telemetry.metrics()
    (sent,) = metrics["messaging.client.sent.messages"]
    assert sent.value == 2
    assert sent.attributes["messaging.destination.name"] == "pris:A"
    (duration,) = metrics["messaging.client.operation.duration"]
    assert duration.count == 2
    assert list(duration.explicit_bounds)[:3] == [0.005, 0.01, 0.025]


def test_publish_error(instrument, telemetry, channel):
    instrument()
    channel._channel.error = ConnectionError("broker gone")

    with pytest.raises(ConnectionError):
        channel.publish(Message(), topic="A")

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


def test_publish_hook(instrument, telemetry, channel):
    calls = []

    def hook(span, message):
        calls.append((span.name, message))
        span.set_attribute("custom", "yes")

    instrument(publish_hook=hook)
    message = Message()
    channel.publish(message, topic="A")

    assert calls == [("publish A", message)]
    assert telemetry.spans()[0].attributes["custom"] == "yes"


def test_failing_hook_does_not_break_publish(instrument, telemetry, channel):
    def hook(span, message):
        raise ValueError("bug in hook")

    instrument(publish_hook=hook)
    channel.publish(Message(), topic="A")

    assert len(channel._channel.published) == 1
    assert len(telemetry.spans()) == 1


def test_uninstrument(instrument, telemetry, channel):
    instrument()
    PrisWireInstrumentor().uninstrument()

    channel.publish(Message(), topic="A")

    assert telemetry.spans() == ()
    assert len(channel._channel.published) == 1

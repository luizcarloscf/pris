import pytest
from google.protobuf.struct_pb2 import Struct
from pris_wire.core import Message, Status, StatusCode, Subscription, now
from pris_wire.rpc import ServiceProvider
from opentelemetry.instrumentation.pris_wire import PrisWireInstrumentor
from opentelemetry.trace import SpanKind, StatusCode as SpanStatusCode


def call(channel, provider, topic="Echo.Run", timeout=None):
    replies = Subscription(channel)
    request = Message(content=Struct(), reply_to=replies)
    if timeout is not None:
        request.timeout = timeout
    channel.publish(request, topic=topic)
    channel.connection.loopback()
    provider.serve(channel.consume())
    channel.connection.loopback()
    return channel.consume(timeout=0.0)


@pytest.fixture
def provider(channel):
    provider = ServiceProvider(channel)
    provider.delegate("Echo.Run", lambda request, context: request, Struct, Struct)
    return provider


def test_rpc_trace(instrument, telemetry, channel):
    tracer = telemetry.tracer_provider.get_tracer("handler")

    def traced_echo(request, context):
        with tracer.start_as_current_span("handler work"):
            return request

    instrument()
    provider = ServiceProvider(channel)
    provider.delegate("Echo.Run", traced_echo, Struct, Struct)

    reply = call(channel, provider)

    assert reply.status.code == StatusCode.OK
    spans = {span.name: span for span in telemetry.spans()}
    request, server = spans["publish Echo.Run"], spans["Echo.Run"]
    handler, reply_span = spans["handler work"], spans["publish (reply)"]

    assert server.kind == SpanKind.SERVER
    receive = spans["receive Echo.Run"]
    assert receive.parent.span_id == request.context.span_id
    assert server.parent.span_id == receive.context.span_id
    assert handler.parent.span_id == server.context.span_id
    assert reply_span.parent.span_id == server.context.span_id
    assert {s.context.trace_id for s in (request, server, handler, reply_span)} == \
        {request.context.trace_id}
    assert dict(server.attributes) == {
        "rpc.system.name": "pris_wire",
        "rpc.method": "Echo.Run",
        "rpc.response.status_code": "OK",
    }
    assert server.status.status_code == SpanStatusCode.UNSET

    (duration,) = telemetry.metrics()["rpc.server.call.duration"]
    assert duration.count == 1
    assert dict(duration.attributes) == dict(server.attributes)


def test_client_error_status_keeps_span_unset(instrument, telemetry, channel):
    instrument()
    provider = ServiceProvider(channel)
    provider.delegate("Find.Thing", lambda request, context: Status(StatusCode.NOT_FOUND, "no"),
                      Struct, Struct)

    reply = call(channel, provider, topic="Find.Thing")

    assert reply.status.code == StatusCode.NOT_FOUND
    server = next(s for s in telemetry.spans() if s.kind == SpanKind.SERVER)
    assert server.attributes["rpc.response.status_code"] == "NOT_FOUND"
    assert server.attributes["error.type"] == "NOT_FOUND"
    assert server.status.status_code == SpanStatusCode.UNSET


def test_handler_exception_is_server_error(instrument, telemetry, channel):
    def broken(request, context):
        raise ValueError("bug")

    instrument()
    provider = ServiceProvider(channel)
    provider.delegate("Broken.Run", broken, Struct, Struct)

    reply = call(channel, provider, topic="Broken.Run")

    assert reply.status.code == StatusCode.INTERNAL_ERROR
    server = next(s for s in telemetry.spans() if s.kind == SpanKind.SERVER)
    assert server.status.status_code == SpanStatusCode.ERROR
    assert server.attributes["error.type"] == "INTERNAL_ERROR"
    (duration,) = telemetry.metrics()["rpc.server.call.duration"]
    assert duration.attributes["rpc.response.status_code"] == "INTERNAL_ERROR"


def test_deadline_exceeded(instrument, telemetry, channel, provider):
    instrument()
    replies = Subscription(channel)
    request = Message(content=Struct(), reply_to=replies)
    request.timeout = 0.5
    request.created_at = now() - 10.0
    channel.publish(request, topic="Echo.Run")
    channel.connection.loopback()

    provider.serve(channel.consume())

    server = next(s for s in telemetry.spans() if s.kind == SpanKind.SERVER)
    assert server.attributes["rpc.response.status_code"] == "DEADLINE_EXCEEDED"
    assert server.status.status_code == SpanStatusCode.ERROR
    assert not any(s.name == "publish (reply)" for s in telemetry.spans())


def test_unknown_subscription(instrument, telemetry, channel, provider):
    instrument()
    message = Message()
    message.topic = "Not.Delegated"
    message.subscription_id = "nobody"

    with pytest.raises(RuntimeError):
        provider.serve(message)

    (server,) = telemetry.spans()
    assert server.name == "pris_wire"
    assert server.attributes["rpc.method"] == "_OTHER"
    assert server.attributes["error.type"] == "RuntimeError"
    assert server.status.status_code == SpanStatusCode.ERROR


def test_request_and_response_hooks(instrument, telemetry, channel, provider):
    calls = []
    instrument(
        request_hook=lambda span, request: calls.append(("request", request.topic)),
        response_hook=lambda span, reply: calls.append(("response", reply.status.code)),
    )

    call(channel, provider)

    assert calls == [("request", "Echo.Run"), ("response", StatusCode.OK)]


def test_provider_created_before_instrument(telemetry, channel, provider, instrument):
    instrument()

    call(channel, provider)

    server = next(s for s in telemetry.spans() if s.kind == SpanKind.SERVER)
    assert server.attributes["rpc.response.status_code"] == "OK"


def test_uninstrumented_provider_keeps_working(instrument, telemetry, channel, provider):
    instrument()
    call(channel, provider)
    PrisWireInstrumentor().uninstrument()
    count = len(telemetry.spans())

    reply = call(channel, provider)

    assert reply.status.code == StatusCode.OK
    assert len(telemetry.spans()) == count

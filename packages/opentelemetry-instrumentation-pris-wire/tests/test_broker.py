import os
import threading
import uuid

from google.protobuf.struct_pb2 import Struct
from pris_wire.core import Channel, Message, StatusCode, Subscription
from pris_wire.rpc import ServiceProvider
from opentelemetry.trace import SpanKind

URI = os.getenv("WIRE_RABBITMQ_URI", "amqp://guest:guest@localhost:5672")


def test_rpc_over_broker(instrument, telemetry):
    instrument()
    topic = "OtelTest.{}.Echo".format(uuid.uuid4().hex[:8])

    server_channel = Channel(URI)
    provider = ServiceProvider(server_channel)
    provider.delegate(topic, lambda request, context: request, Struct, Struct)
    server = threading.Thread(
        target=lambda: provider.serve(server_channel.consume(timeout=5.0)), daemon=True)
    server.start()

    client = Channel(URI)
    replies = Subscription(client)
    request = Struct()
    request.update({"value": 42})
    tracer = telemetry.tracer_provider.get_tracer("client")
    with tracer.start_as_current_span("client call"):
        client.publish(Message(content=request, reply_to=replies), topic=topic)
        reply = client.consume(timeout=5.0)
    server.join(timeout=5.0)
    client.close()
    server_channel.close()

    assert reply.status.code == StatusCode.OK
    assert reply.unpack(Struct) == request

    spans = {span.name: span for span in telemetry.spans()}
    root = spans["client call"]
    publish, served = spans["publish " + topic], spans[topic]
    reply_publish, reply_receive = spans["publish (reply)"], spans["receive (reply)"]
    request_receive = spans["receive " + topic]

    assert publish.parent.span_id == root.context.span_id
    assert served.kind == SpanKind.SERVER
    assert served.parent.span_id == request_receive.context.span_id
    assert reply_publish.parent.span_id == served.context.span_id
    assert {s.context.trace_id for s in (root, publish, served, reply_publish)} == \
        {root.context.trace_id}
    assert reply_receive.parent.span_id == root.context.span_id
    assert reply_receive.links[0].context.span_id == reply_publish.context.span_id
    assert request_receive.parent.span_id == publish.context.span_id
    assert request_receive.links[0].context.span_id == publish.context.span_id

    metrics = telemetry.metrics()
    for name in ("messaging.client.sent.messages",
                 "messaging.client.consumed.messages",
                 "messaging.client.operation.duration",
                 "rpc.server.call.duration"):
        assert name in metrics, name
    (call_duration,) = metrics["rpc.server.call.duration"]
    assert call_duration.attributes["rpc.response.status_code"] == "OK"

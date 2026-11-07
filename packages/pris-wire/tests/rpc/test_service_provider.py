import os
import socket
import threading
import time

import pytest
from google.protobuf.struct_pb2 import Struct
from google.protobuf.wrappers_pb2 import Int64Value

from pris_wire.core import Channel, Message, Status, StatusCode, Subscription
from pris_wire.rpc import LogInterceptor, ServiceProvider

URI = os.getenv('WIRE_RABBITMQ_URI', 'amqp://guest:guest@localhost:5672')


def my_service(request, context):
    value = int(request.fields["value"].number_value)
    if value == 666:
        return Status(StatusCode.FAILED_PRECONDITION, "Cant be zero")
    if value == 10:
        raise RuntimeError("Unexpected error")
    reply = Int64Value(value=value)
    return reply


def test_rpc():
    channel = Channel(uri=URI)
    service = ServiceProvider(channel)
    service.add_interceptor(LogInterceptor())
    service.delegate("MyService", my_service, Struct, Int64Value)

    subscription = Subscription(channel)

    def request_serve_consume(number):
        struct = Struct()
        struct.fields["value"].number_value = number
        message = Message(struct)
        message.reply_to = subscription
        message.pack(struct)
        channel.publish(topic="MyService", message=message)

        request = channel.consume(timeout=1.0)
        assert request.body == message.body
        service.serve(request)
        assert request.unpack(Struct) == struct

        return channel.consume(timeout=1.0)

    reply = request_serve_consume(90.0)
    int64 = reply.unpack(Int64Value)
    assert int64.value == 90
    assert reply.status.ok() is True

    reply = request_serve_consume(666.0)
    assert reply.status.ok() is False
    assert reply.status.code == StatusCode.FAILED_PRECONDITION

    reply = request_serve_consume(10.0)
    assert reply.status.ok() is False
    assert reply.status.code == StatusCode.INTERNAL_ERROR

    channel.close()


def test_serve():
    channel = Channel(uri=URI)
    service = ServiceProvider(channel)
    topic = "MyService"
    service.delegate(topic, my_service, Struct, Int64Value)

    subscription = Subscription(channel)

    sent = Message(content=b"body")
    channel.publish(sent, topic=subscription.name)

    recv = channel.consume(timeout=1.0)
    assert recv.subscription_id == subscription.id

    assert service.should_serve(recv) is False
    with pytest.raises(RuntimeError):
        service.serve(recv)

    sent.topic = topic
    channel.publish(message=sent)
    recv = channel.consume(timeout=1.0)

    assert service.should_serve(recv) is True
    service.serve(recv)

    channel.close()


def test_burst_loses_nothing():
    requests = 100
    topic = "MyService.Burst"
    served = []
    ready, stop = threading.Event(), threading.Event()

    def server():
        channel = Channel(uri=URI)
        service = ServiceProvider(channel)
        service.delegate(topic, lambda request, context: served.append(1) or request,
                         Struct, Struct)
        ready.set()
        while not stop.is_set():
            try:
                service.serve(channel.consume(timeout=0.1))
            except socket.timeout:
                pass
        channel.close()

    thread = threading.Thread(target=server, daemon=True)
    thread.start()
    assert ready.wait(timeout=5.0)

    client = Channel(uri=URI)
    subscription = Subscription(client)
    pending = set()
    for _ in range(requests):
        message = Message(Struct(), reply_to=subscription)
        client.publish(message, topic=topic)
        pending.add(message.correlation_id)

    deadline = time.monotonic() + 10.0
    try:
        while pending:
            reply = client.consume(timeout=max(0.0, deadline - time.monotonic()))
            assert reply.status.ok() is True
            pending.discard(reply.correlation_id)
    except socket.timeout:
        pass
    finally:
        stop.set()
        thread.join(timeout=5.0)
        client.close()

    assert len(served) == requests
    assert not pending


def test_delegate():
    channel = Channel(uri=URI)
    service = ServiceProvider(channel)
    service.delegate("MyService", my_service, Struct, Int64Value)
    with pytest.raises(RuntimeError):
        service.delegate("MyService", my_service, Struct, Int64Value)
    channel.close()

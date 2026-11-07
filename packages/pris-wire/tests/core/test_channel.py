import os
import socket
import time

import pytest
from google.protobuf.struct_pb2 import Struct

from pris_wire.core import Channel, Message, Subscription, now

URI = os.getenv('WIRE_RABBITMQ_URI', 'amqp://guest:guest@localhost:5672')


def test_channel():
    channel = Channel(uri=URI)
    subscription = Subscription(channel)
    subscription.subscribe("MyTopic.Sub.Sub")

    struct = Struct()
    struct.fields["value"].number_value = 666.0

    sent = Message(struct)
    sent.reply_to = subscription
    sent.created_at = int(1000 * now()) / 1000.0
    sent.timeout = 1.0
    sent.topic = "MyTopic.Sub.Sub"

    channel.publish(message=sent)
    received = channel.consume(timeout=1.0)

    assert str(received) == str(sent)
    assert received.unpack(Struct) == struct

    channel.close()


@pytest.mark.parametrize("size", [0, 1e4])
def test_body(size):
    channel = Channel(uri=URI)

    subscription = Subscription(channel)
    subscription.subscribe("MyTopic.Sub.Sub")

    sent = Message()
    sent.reply_to = subscription
    sent.topic = "MyTopic.Sub.Sub"
    sent.body = bytes(bytearray(range(256)) * int(size))

    channel.publish(message=sent)
    received = channel.consume(timeout=1.0)

    assert received.body == sent.body

    channel.close()


def test_negative_timeout():
    channel = Channel(uri=URI)
    with pytest.raises(AssertionError):
        channel.consume(timeout=-1e-10)
    with pytest.raises(socket.timeout):
        channel.consume(timeout=0)
    channel.close()


def test_consume_for_until_ready():
    channel = Channel(uri=URI)
    subscription = Subscription(channel)

    assert channel.consume_for(0.05) is None
    assert channel.consume_until(time.time() + 0.05) is None
    assert channel.consume_ready() == []

    channel.publish(Message(content=b"for"), topic=subscription.name)
    assert channel.consume_for(1.0).body == b"for"

    channel.publish(Message(content=b"until"), topic=subscription.name)
    assert channel.consume_until(time.time() + 1.0).body == b"until"

    for body in (b"1", b"2", b"3"):
        channel.publish(Message(content=body), topic=subscription.name)
    received = []
    deadline = time.time() + 1.0
    while len(received) < 3 and time.time() < deadline:
        received += channel.consume_ready()
    assert [message.body for message in received] == [b"1", b"2", b"3"]
    channel.close()


def test_empty_topic():
    channel = Channel(uri=URI)
    message = Message(content=b"body")

    with pytest.raises(RuntimeError):
        channel.publish(message)

    with pytest.raises(RuntimeError):
        channel.publish(message, topic="")

    subscription = Subscription(channel)
    channel.publish(message, topic=subscription.name)
    recv = channel.consume(timeout=1.0)
    assert recv.body == message.body

    message.topic = subscription.name
    channel.publish(message)
    recv = channel.consume(timeout=1.0)
    assert recv.body == message.body
    channel.close()


def test_multi_subscription():
    channel = Channel(uri=URI)
    message = Message()
    subscription1 = Subscription(channel)
    subscription2 = Subscription(channel)

    channel.publish(message, topic=subscription1.name)
    recv = channel.consume(timeout=1.0)
    assert recv.subscription_id == subscription1.name

    channel.publish(message, topic=subscription2.name)
    recv = channel.consume(timeout=1.0)
    assert recv.subscription_id == subscription2.name
    channel.close()

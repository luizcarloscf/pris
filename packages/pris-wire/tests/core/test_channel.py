import socket
import time

import pytest
from google.protobuf.struct_pb2 import Struct

from pris_wire.core import Message, Subscription, now


def test_channel(channel, topic):
    subscription = Subscription(channel)
    subscription.subscribe(topic)

    struct = Struct()
    struct.fields["value"].number_value = 666.0

    sent = Message(struct)
    sent.reply_to = subscription
    sent.created_at = int(1000 * now()) / 1000.0
    sent.timeout = 1.0
    sent.topic = topic

    channel.publish(message=sent)
    received = channel.consume(timeout=1.0)

    assert str(received) == str(sent)
    assert received.unpack(Struct) == struct


@pytest.mark.parametrize("size", [0, 1e4])
def test_body(channel, size):
    subscription = Subscription(channel)
    sent = Message()
    sent.body = bytes(bytearray(range(256)) * int(size))

    channel.publish(sent, topic=subscription.name)

    assert channel.consume(timeout=1.0).body == sent.body


def test_messages_keep_their_order(channel):
    subscription = Subscription(channel)
    for body in (b"1", b"2", b"3"):
        channel.publish(Message(content=body), topic=subscription.name)

    assert [channel.consume(timeout=1.0).body for _ in range(3)] == [b"1", b"2", b"3"]


def test_negative_timeout(channel):
    with pytest.raises(AssertionError):
        channel.consume(timeout=-1e-10)
    with pytest.raises(socket.timeout):
        channel.consume(timeout=0)


def test_consume_for_until_ready(channel):
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


def test_past_deadlines_do_not_wait(channel):
    Subscription(channel)
    start = time.monotonic()

    assert channel.consume_for(-1.0) is None
    assert channel.consume_until(time.time() - 1.0) is None

    assert time.monotonic() - start < 0.05


def test_empty_topic(channel):
    message = Message(content=b"body")

    with pytest.raises(RuntimeError):
        channel.publish(message)

    with pytest.raises(RuntimeError):
        channel.publish(message, topic="")

    subscription = Subscription(channel)
    channel.publish(message, topic=subscription.name)
    assert channel.consume(timeout=1.0).body == message.body

    message.topic = subscription.name
    channel.publish(message)
    assert channel.consume(timeout=1.0).body == message.body


def test_multi_subscription(channel):
    message = Message()
    subscription1 = Subscription(channel)
    subscription2 = Subscription(channel)

    channel.publish(message, topic=subscription1.name)
    assert channel.consume(timeout=1.0).subscription_id == subscription1.name

    channel.publish(message, topic=subscription2.name)
    assert channel.consume(timeout=1.0).subscription_id == subscription2.name

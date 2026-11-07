import os
import time
import uuid

from pris_wire.core import Channel, Message, Subscription

URI = os.getenv('WIRE_RABBITMQ_URI', 'amqp://guest:guest@localhost:5672')


def unique(prefix):
    return "{}.{}".format(prefix, uuid.uuid4().hex[:8])


def bodies(messages):
    return [message.body for message in messages]


def test_a_max_length_of_one_keeps_only_the_newest():
    channel = Channel(uri=URI)
    topic = unique("Latest")
    subscription = Subscription(channel, arguments={"x-max-length": 1,
                                                    "x-overflow": "drop-head"},
                                prefetch=1, manual_ack=True)
    subscription.subscribe(topic)
    publisher = Channel(uri=URI)
    try:
        for n in range(5):
            publisher.publish(Message(content=str(n).encode()), topic=topic)
        first = channel.consume(timeout=1.0)
        time.sleep(0.2)
        channel.ack(first)
        newest = channel.consume(timeout=1.0)
        channel.ack(newest)
        assert (first.body, newest.body) == (b"0", b"4")
        assert channel.consume_for(0.2) is None
    finally:
        channel.close()
        publisher.close()


def test_manual_ack_redelivers_until_acknowledged():
    name = unique("Work")
    channel = Channel(uri=URI)
    subscription = Subscription(channel, name=name, prefetch=1, manual_ack=True)
    try:
        channel.publish(Message(content=b"job"), topic=name)
        message = channel.consume(timeout=1.0)
        assert message.body == b"job" and message.has_delivery_tag()
        channel.reject(message, requeue=True)
        again = channel.consume(timeout=1.0)
        assert again.body == b"job"
        channel.ack(again)
        assert channel.consume_for(0.3) is None
        assert subscription.manual_ack
    finally:
        channel.close()


def test_prefetch_one_spreads_work_between_consumers():
    name = unique("Shared")
    busy, idle = Channel(uri=URI), Channel(uri=URI)
    Subscription(busy, name=name, prefetch=1, manual_ack=True)
    Subscription(idle, name=name, prefetch=1, manual_ack=True)
    publisher = Channel(uri=URI)
    try:
        for n in range(4):
            publisher.publish(Message(content=str(n).encode()), topic=name)
        held = busy.consume(timeout=1.0)
        handled = []
        for _ in range(3):
            message = idle.consume(timeout=1.0)
            handled.append(message.body)
            idle.ack(message)
        assert busy.consume_for(0.2) is None
        assert sorted([held.body] + handled) == [b"0", b"1", b"2", b"3"]
    finally:
        for channel in (busy, idle, publisher):
            channel.close()


def test_a_different_prefetch_does_not_leak_to_later_subscriptions():
    channel = Channel(uri=URI)
    limited = Subscription(channel, name=unique("Limited"), prefetch=1, manual_ack=True)
    plain = Subscription(channel)
    try:
        for n in range(3):
            channel.publish(Message(content=str(n).encode()), topic=plain.name)
        received = [channel.consume(timeout=1.0) for _ in range(3)]
        assert bodies(received) == [b"0", b"1", b"2"]
        assert all(m.subscription_id == plain.id for m in received)
        assert limited.manual_ack and not plain.manual_ack
    finally:
        channel.close()

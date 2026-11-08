import time

import amqp
import pytest
from pris_wire.core import Message, Subscription


def bodies(messages):
    return [message.body for message in messages]


def test_private_queue_is_exclusive(channel, connect):
    subscription = Subscription(channel)

    with pytest.raises(amqp.exceptions.ResourceLocked):
        connect()._channel.queue_declare(queue=subscription.name, passive=True)


def test_named_queue_is_durable(channel, connect, topic):
    Subscription(channel, name=topic)

    with pytest.raises(amqp.exceptions.PreconditionFailed):
        connect()._channel.queue_declare(queue=topic, durable=False, auto_delete=True)


def test_messages_are_acknowledged_by_default(connect, topic):
    first, second = connect(), connect()
    subscription = Subscription(first, name=topic)
    first.publish(Message(content=b"job"), topic=topic)
    assert first.consume(timeout=1.0).body == b"job"
    Subscription(second, name=topic)

    first.close()

    assert subscription.manual_ack is False
    assert second.consume_for(0.3) is None


def test_a_max_length_of_one_keeps_only_the_newest(channel, connect, topic):
    subscription = Subscription(channel, arguments={"x-max-length": 1, "x-overflow": "drop-head"},
                                prefetch=1, manual_ack=True)
    subscription.subscribe(topic)
    publisher = connect()
    for n in range(5):
        publisher.publish(Message(content=str(n).encode()), topic=topic)

    first = channel.consume(timeout=1.0)
    time.sleep(0.2)
    channel.ack(first)
    newest = channel.consume(timeout=1.0)
    channel.ack(newest)

    assert (first.body, newest.body) == (b"0", b"4")
    assert channel.consume_for(0.2) is None


def test_manual_ack_redelivers_until_acknowledged(channel, topic):
    subscription = Subscription(channel, name=topic, prefetch=1, manual_ack=True)
    channel.publish(Message(content=b"job"), topic=topic)

    message = channel.consume(timeout=1.0)
    assert message.body == b"job" and message.has_delivery_tag()
    channel.reject(message, requeue=True)
    again = channel.consume(timeout=1.0)
    assert again.body == b"job"
    channel.ack(again)

    assert channel.consume_for(0.3) is None
    assert subscription.manual_ack


def test_reject_drops_the_message(channel, topic):
    Subscription(channel, name=topic, prefetch=1, manual_ack=True)
    channel.publish(Message(content=b"job"), topic=topic)

    channel.reject(channel.consume(timeout=1.0))

    assert channel.consume_for(0.3) is None
    with pytest.raises(ValueError, match="no delivery tag"):
        channel.ack(Message())


def test_prefetch_one_spreads_work_between_consumers(connect, topic):
    busy, idle, publisher = connect(), connect(), connect()
    Subscription(busy, name=topic, prefetch=1, manual_ack=True)
    Subscription(idle, name=topic, prefetch=1, manual_ack=True)
    for n in range(4):
        publisher.publish(Message(content=str(n).encode()), topic=topic)

    held = busy.consume(timeout=1.0)
    handled = []
    for _ in range(3):
        message = idle.consume(timeout=1.0)
        handled.append(message.body)
        idle.ack(message)

    assert busy.consume_for(0.2) is None
    assert sorted([held.body] + handled) == [b"0", b"1", b"2", b"3"]


def test_a_different_prefetch_does_not_leak_to_later_subscriptions(channel, topic):
    limited = Subscription(channel, name=topic, prefetch=1, manual_ack=True)
    plain = Subscription(channel)
    for n in range(3):
        channel.publish(Message(content=str(n).encode()), topic=plain.name)

    received = [channel.consume(timeout=1.0) for _ in range(3)]

    assert bodies(received) == [b"0", b"1", b"2"]
    assert all(m.subscription_id == plain.id for m in received)
    assert limited.manual_ack and not plain.manual_ack


@pytest.mark.parametrize("kwargs, match", [
    ({"prefetch": 1}, "needs manual_ack"),
    ({"prefetch": 0, "manual_ack": True}, "positive"),
    ({"prefetch": 1.5, "manual_ack": True}, "positive"),
])
def test_invalid_prefetch(channel, kwargs, match):
    with pytest.raises(ValueError, match=match):
        Subscription(channel, **kwargs)

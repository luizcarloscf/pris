from types import SimpleNamespace

import pytest
from pris_wire.core import Channel, Message, Subscription
from pris_wire.core.wire.conversion import WireV1


class RecordingAmqpChannel:

    def __init__(self):
        self.declared = []
        self.consumers = []
        self.calls = []

    def queue_declare(self, **kwargs):
        self.declared.append(kwargs)

    def queue_bind(self, **kwargs):
        pass

    def basic_consume(self, **kwargs):
        self.consumers.append(kwargs)
        self.calls.append(("consume", kwargs["consumer_tag"]))

    def basic_qos(self, **kwargs):
        self.calls.append(("qos", kwargs["prefetch_count"]))

    def basic_ack(self, **kwargs):
        self.calls.append(("ack", kwargs))

    def basic_reject(self, **kwargs):
        self.calls.append(("reject", kwargs))


def make_channel():
    return SimpleNamespace(_channel=RecordingAmqpChannel(), _exchange="pris",
                           _on_message=lambda message: None, _prefetch=0)


def test_private_queue_is_exclusive():
    channel = make_channel()
    subscription = Subscription(channel)

    (declared,) = channel._channel.declared
    assert declared["queue"] == subscription.name
    assert declared["exclusive"] is True
    assert declared["durable"] is False
    assert declared["auto_delete"] is True


def test_named_queue_is_durable_and_shareable():
    channel = make_channel()
    Subscription(channel, name="CameraGateway.0.GetConfig")

    (declared,) = channel._channel.declared
    assert declared["queue"] == "CameraGateway.0.GetConfig"
    assert declared["exclusive"] is False
    assert declared["durable"] is True
    assert declared["auto_delete"] is True
    (consumer,) = channel._channel.consumers
    assert consumer["exclusive"] is False


def test_defaults_are_unchanged():
    channel = make_channel()
    subscription = Subscription(channel)

    (declared,) = channel._channel.declared
    assert declared["arguments"] == {}
    (consumer,) = channel._channel.consumers
    assert consumer["no_ack"] is True
    assert subscription.manual_ack is False
    assert [call for call in channel._channel.calls if call[0] == "qos"] == []


def test_queue_arguments_reach_the_broker():
    channel = make_channel()
    arguments = {"x-max-length": 1, "x-overflow": "drop-head"}
    Subscription(channel, name="bridge.robot1.tf.latest", arguments=arguments)

    (declared,) = channel._channel.declared
    assert declared["arguments"] == arguments
    assert declared["arguments"] is not arguments


def test_manual_ack_and_prefetch():
    channel = make_channel()
    subscription = Subscription(channel, name="work", prefetch=2, manual_ack=True)

    assert subscription.manual_ack is True
    (consumer,) = channel._channel.consumers
    assert consumer["no_ack"] is False
    assert channel._channel.calls == [("qos", 2), ("consume", subscription.id)]


def test_prefetch_is_set_back_for_the_next_consumers():
    channel = make_channel()
    first = Subscription(channel, prefetch=1, manual_ack=True)
    second = Subscription(channel, prefetch=1, manual_ack=True)
    third = Subscription(channel)
    fourth = Subscription(channel)

    assert channel._channel.calls == [
        ("qos", 1), ("consume", first.id),
        ("consume", second.id),
        ("qos", 0), ("consume", third.id),
        ("consume", fourth.id),
    ]


@pytest.mark.parametrize("kwargs, match", [
    ({"prefetch": 1}, "needs manual_ack"),
    ({"prefetch": 0, "manual_ack": True}, "positive"),
    ({"prefetch": 1.5, "manual_ack": True}, "positive"),
])
def test_invalid_prefetch(kwargs, match):
    with pytest.raises(ValueError, match=match):
        Subscription(make_channel(), **kwargs)


def test_received_messages_carry_their_delivery_tag():
    amqp_message = SimpleNamespace(body=b"", properties={}, delivery_info={
        "routing_key": "topic", "consumer_tag": "tag", "delivery_tag": 42})
    assert WireV1.from_amqp_message(amqp_message).delivery_tag == 42
    del amqp_message.delivery_info["delivery_tag"]
    assert not WireV1.from_amqp_message(amqp_message).has_delivery_tag()
    assert not Message().has_delivery_tag()


def test_ack_and_reject():
    channel = Channel.__new__(Channel)
    channel._channel = RecordingAmqpChannel()
    message = Message()
    message.delivery_tag = 7

    channel.ack(message)
    channel.reject(message)
    channel.reject(message, requeue=True)

    assert channel._channel.calls == [
        ("ack", {"delivery_tag": 7}),
        ("reject", {"delivery_tag": 7, "requeue": False}),
        ("reject", {"delivery_tag": 7, "requeue": True}),
    ]
    with pytest.raises(ValueError, match="no delivery tag"):
        channel.ack(Message())

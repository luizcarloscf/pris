import pytest
from pris_msgs.common_pb2 import ConsumerList
from pris_wire.core import Message

from pris_broker_events.service import BrokerEvents


def binding(routing_key, destination, source="pris", destination_type="queue"):
    return {"source": source, "destination": destination, "destination_type": destination_type,
            "routing_key": routing_key}


def event(kind, routing_key, queue, source_name="pris", destination_kind="queue"):
    message = Message()
    message.topic = "binding.{}".format(kind)
    message.metadata = {"source_name": source_name, "destination_name": queue,
                        "destination_kind": destination_kind, "routing_key": routing_key}
    return message


def consumer_map(consumers):
    return {topic: list(info.consumers) for topic, info in consumers.info.items()}


def test_consumers_from_bindings():
    consumers = BrokerEvents.consumers_from_bindings([
        binding("CameraGateway.0.GetConfig", "CameraGateway.0.GetConfig"),
        binding("CameraGateway.*.Frame", "ArUco.Localization"),
        binding("CameraGateway.*.Frame", "host/1A2B"),
        binding("anything", "pris", source="amq.rabbitmq.event", destination_type="exchange"),
        binding("Other", "queue", source=""),
    ])

    assert consumer_map(consumers) == {
        "CameraGateway.0.GetConfig": ["CameraGateway.0.GetConfig"],
        "CameraGateway.*.Frame": ["ArUco.Localization", "host/1A2B"],
    }


def test_created_adds_a_consumer():
    consumers = ConsumerList()

    assert BrokerEvents.apply_event(consumers, event("created", "Topic.A", "queue-1"))
    assert BrokerEvents.apply_event(consumers, event("created", "Topic.A", "queue-2"))

    assert consumer_map(consumers) == {"Topic.A": ["queue-1", "queue-2"]}


def test_a_known_consumer_is_kept_once():
    consumers = BrokerEvents.consumers_from_bindings([binding("Topic.A", "queue-1")])

    assert BrokerEvents.apply_event(consumers, event("created", "Topic.A", "queue-1"))

    assert consumer_map(consumers) == {"Topic.A": ["queue-1"]}


def test_deleted_removes_the_consumer_and_an_empty_topic():
    consumers = BrokerEvents.consumers_from_bindings([
        binding("Topic.A", "queue-1"), binding("Topic.A", "queue-2"), binding("Topic.B", "q"),
    ])

    assert BrokerEvents.apply_event(consumers, event("deleted", "Topic.A", "queue-1"))
    assert consumer_map(consumers) == {"Topic.A": ["queue-2"], "Topic.B": ["q"]}
    assert BrokerEvents.apply_event(consumers, event("deleted", "Topic.A", "queue-2"))
    assert consumer_map(consumers) == {"Topic.B": ["q"]}


def test_deleted_for_an_unknown_topic_is_harmless():
    consumers = BrokerEvents.consumers_from_bindings([binding("Topic.B", "q")])

    assert BrokerEvents.apply_event(consumers, event("deleted", "Topic.Unknown", "queue-1"))

    assert consumer_map(consumers) == {"Topic.B": ["q"]}


@pytest.mark.parametrize("message", [
    event("created", "Topic.A", "pris", destination_kind="exchange"),
    event("created", "#", "pris", source_name="amq.rabbitmq.event"),
])
def test_events_not_about_consumers_are_ignored(message):
    consumers = ConsumerList()

    assert not BrokerEvents.apply_event(consumers, message)
    assert consumer_map(consumers) == {}


def test_another_exchange():
    bindings = [binding("Topic.A", "queue-1"), binding("Topic.B", "queue-2", source="other")]

    consumers = BrokerEvents.consumers_from_bindings(bindings, exchange="other")

    assert consumer_map(consumers) == {"Topic.B": ["queue-2"]}
    assert BrokerEvents.apply_event(consumers, event("created", "Topic.C", "q", "other"), "other")
    assert not BrokerEvents.apply_event(consumers, event("created", "Topic.D", "q"), "other")

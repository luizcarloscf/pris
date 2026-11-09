import time
from pathlib import Path

import numpy as np
import pytest
from pris_msgs.camera_pb2 import (
    FrameTransformation,
    FrameTransformations,
    GetTransformationReply,
    GetTransformationRequest,
    IdPair,
)
from pris_msgs.common_pb2 import ConsumerList
from pris_msgs.utils.io import load
from pris_msgs.utils.tensor import to_array, to_tensor
from pris_wire.core import Message, StatusCode, Subscription

from pris_frame_transformation.conf.options_pb2 import FrameTransformationOptions
from pris_frame_transformation.graph import invert
from pris_frame_transformation.service import FrameTransformationService

DEFAULT_OPTIONS = Path(__file__).parents[1] / "etc" / "conf" / "options.json"


def marker_pose(x, y, z, yaw):
    c, s = np.cos(yaw), np.sin(yaw)
    pose = np.eye(4)
    pose[:2, :2] = [[c, -s], [s, c]]
    pose[:3, 3] = [x, y, z]
    return pose


def transformations(*items):
    message = FrameTransformations()
    for source, target, matrix, expiration in items:
        tf = message.tfs.add(source=source, target=target, tf=to_tensor(matrix))
        if expiration is not None:
            tf.expiration.FromNanoseconds(int(expiration * 1e9))
    return message


def consumers(*topics):
    result = ConsumerList()
    for topic in topics:
        result.info[topic].consumers.append("queue")
    return result


class Broker:

    def __init__(self, service, channel, topic):
        self.service = service
        self.channel = channel
        self.topic = topic

    def publish(self, content, suffix, created_at=None):
        message = Message(content=content)
        if created_at is not None:
            message.created_at = created_at
        self.channel.publish(message, topic="{}.{}".format(self.topic, suffix))

    def step(self):
        time.sleep(0.1)
        return self.service.step(timeout=0.5)


@pytest.fixture
def service(channel, labvisio, topic):
    return FrameTransformationService(
        channel, [labvisio[0], labvisio[1]],
        consumers_topic=topic + ".Consumers",
        transformations_topic=topic + ".FrameTransformations",
        get_transformation_topic=topic + ".GetTransformation",
    )


@pytest.fixture
def broker(service, connect, topic):
    return Broker(service, connect(), topic)


def test_default_options():
    options = load(str(DEFAULT_OPTIONS), FrameTransformationOptions)

    assert options.broker_uri == "amqp://guest:guest@rabbitmq.pris"
    assert list(options.camera_ids) == [0, 1, 2, 3]
    assert options.telemetry.otlp_endpoint == "http://otel-collector.pris:4318"


def test_calibrations_become_static_edges(service, labvisio):
    edge = service.graph.edges[(1, 1000)]

    assert edge.static
    np.testing.assert_allclose(edge.matrix, to_array(labvisio[1].extrinsic[0].tf))


def test_watched_paths_are_published_when_they_change(broker, labvisio, spans):
    pose = marker_pose(0.5, -0.2, 0.0, 0.3)
    broker.publish(consumers("FrameTransformation.100.0", "ArUco.0.Detection"), "Consumers")
    assert broker.step() == []

    broker.publish(transformations((100, 1000, pose, time.time() + 10)), "FrameTransformations",
                   created_at=42.0)
    (message,) = broker.step()

    assert message.topic == "FrameTransformation.100.0"
    assert message.created_at == pytest.approx(42.0)
    tf = message.unpack(FrameTransformation)
    assert (tf.source, tf.target) == (100, 0)
    np.testing.assert_allclose(to_array(tf.tf), to_array(labvisio[0].extrinsic[0].tf) @ pose,
                               atol=1e-12)
    assert tf.HasField("expiration")
    assert broker.service.step(timeout=0.2) == []
    (span,) = [s for s in spans.get_finished_spans() if s.name == "update"]
    assert span.attributes["pris.frame_transformation.edges"] == 1
    assert span.attributes["pris.frame_transformation.published"] == ("FrameTransformation.100.0",)


def test_a_batch_publishes_each_path_once(broker):
    broker.publish(consumers("FrameTransformation.100.1"), "Consumers")
    broker.step()
    for x in (0.1, 0.2, 0.3):
        broker.publish(transformations((100, 1000, marker_pose(x, 0, 0, 0), None)),
                       "FrameTransformations")

    (message,) = broker.step()

    tf = message.unpack(FrameTransformation)
    marker_in_world = invert(broker.service.graph.edges[(1, 1000)].matrix) @ to_array(tf.tf)
    np.testing.assert_allclose(marker_in_world[:3, 3], [0.3, 0, 0], atol=1e-12)


def test_expired_edges_stop_publishing_and_resolving(broker):
    broker.publish(consumers("FrameTransformation.100.0"), "Consumers")
    broker.step()
    broker.publish(transformations((100, 1000, np.eye(4), time.time() + 0.3)),
                   "FrameTransformations")
    assert len(broker.step()) == 1
    assert broker.service.next_expiration() is not None

    time.sleep(0.3)

    assert broker.service.step(timeout=0.0) == []
    assert (100, 1000) not in broker.service.graph.edges


def test_dynamic_edges_cant_replace_static_ones(broker):
    static = broker.service.graph.edges[(0, 1000)].matrix

    broker.publish(transformations((1000, 0, np.eye(4), None)), "FrameTransformations")
    broker.step()

    np.testing.assert_allclose(broker.service.graph.edges[(0, 1000)].matrix, static)
    assert (0, 1000) in broker.service.refused


def test_bad_transformations_are_ignored(broker):
    bad = FrameTransformations()
    bad.tfs.add(source=100, target=1000)

    broker.publish(bad, "FrameTransformations")

    assert broker.step() == []
    assert (100, 1000) not in broker.service.graph.edges


def test_get_transformation(broker, labvisio):
    broker.publish(transformations((100, 1000, marker_pose(1, 2, 0, 0), None)),
                   "FrameTransformations")
    broker.step()
    replies = Subscription(broker.channel)

    def call(*pairs):
        request = GetTransformationRequest(ids=[IdPair(source=a, target=b) for a, b in pairs])
        broker.channel.publish(Message(content=request, reply_to=replies),
                               topic=broker.topic + ".GetTransformation")
        broker.step()
        return broker.channel.consume(timeout=1.0)

    reply = call((100, 1), (0, 1))
    assert reply.status.code == StatusCode.OK
    first, second = reply.unpack(GetTransformationReply).transformations
    assert (first.source, first.target) == (100, 1)
    world_to = {id: to_array(labvisio[id].extrinsic[0].tf) for id in (0, 1)}
    np.testing.assert_allclose(to_array(second.tf), world_to[1] @ invert(world_to[0]), atol=1e-9)

    reply = call((100, 1), (100, 7))
    assert reply.status.code == StatusCode.NOT_FOUND
    assert "100 to 7" in reply.status.why


def test_static_edges_of_a_bad_extrinsic(labvisio):
    calibration = labvisio[0]
    calibration.extrinsic[0].tf.shape.dims[0].size = 2

    with pytest.raises(ValueError):
        FrameTransformationService.static_edges(calibration)

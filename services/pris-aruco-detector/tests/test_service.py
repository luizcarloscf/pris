import socket
import time
from pathlib import Path

import pytest
from opentelemetry.trace import SpanKind, StatusCode as SpanStatusCode
from pris_msgs.image_pb2 import Image, ObjectAnnotations
from pris_msgs.utils.io import load
from pris_wire.core import Message, Subscription

from pris_aruco_detector.conf.options_pb2 import ArucoDetectorOptions, DetectorOptions
from pris_aruco_detector.detector import MarkerDetector
from pris_aruco_detector.service import ArucoDetectorService

DEFAULT_OPTIONS = Path(__file__).parents[1] / "etc" / "conf" / "options.json"


@pytest.fixture
def service(channel, topic):
    return ArucoDetectorService(
        channel, MarkerDetector(DetectorOptions()),
        queue_name=topic + ".Detector",
        frame_topic=topic + ".{}.Frame",
        detection_topic=topic + ".{}.Detection",
    )


@pytest.fixture
def camera(connect, topic):
    publisher = connect()
    listener = connect()
    Subscription(listener).subscribe(topic + ".*.Detection")

    def publish(id, image, created_at):
        message = Message(content=image)
        message.created_at = created_at
        publisher.publish(message, topic="{}.{}.Frame".format(topic, id))

    publish.listener = listener
    return publish


def frame(topic, n):
    message = Message(content=Image(data=bytes([n])))
    message.topic = topic
    return message


def test_default_options():
    options = load(str(DEFAULT_OPTIONS), ArucoDetectorOptions)

    assert options.broker_uri == "amqp://guest:guest@rabbitmq.pris"
    assert options.queue_name == "ArUco.Detector"
    assert options.telemetry.otlp_endpoint == "http://otel-collector.pris:4318"


def test_camera_id():
    assert ArucoDetectorService.camera_id("CameraGateway.12.Frame") == 12
    assert ArucoDetectorService.camera_id("CameraGateway.12.Timestamp") is None
    assert ArucoDetectorService.camera_id("CameraGateway.x.Frame") is None
    assert ArucoDetectorService.camera_id("Other.CameraGateway.1.Frame") is None
    assert ArucoDetectorService.camera_id("Lab.3.Image", frame_topic="Lab.{}.Image") == 3


def test_latest_per_camera_keeps_the_newest_of_each_camera():
    messages = [
        frame("CameraGateway.0.Frame", 1),
        frame("CameraGateway.1.Frame", 2),
        frame("CameraGateway.0.Frame", 3),
        frame("BrokerEvents.Consumers", 4),
        frame("CameraGateway.0.Frame", 5),
    ]

    latest = ArucoDetectorService.latest_per_camera(messages)

    assert list(latest) == [0, 1]
    assert latest[0] == (messages[4], 2)
    assert latest[1] == (messages[1], 0)
    assert ArucoDetectorService.latest_per_camera([]) == {}


def test_the_newest_frame_of_each_camera_is_detected(service, camera, scene, topic):
    camera(0, scene([(1, 50, 50)]), 10.0)
    camera(1, scene([]), 10.0)
    camera(0, scene([(2, 50, 50)]), 10.1)
    camera(0, scene([(3, 50, 50), (4, 300, 200)]), 10.2)
    time.sleep(0.2)

    service.step(timeout=1.0)

    detections = [camera.listener.consume(timeout=1.0) for _ in range(2)]
    assert [(m.topic, m.created_at) for m in detections] == [
        (topic + ".0.Detection", 10.2), (topic + ".1.Detection", 10.0)]
    camera0, camera1 = (m.unpack(ObjectAnnotations) for m in detections)
    assert sorted(marker.id for marker in camera0.objects) == [3, 4]
    assert camera0.frame_id == 0
    assert len(camera1.objects) == 0
    assert camera1.frame_id == 1


def test_only_the_given_cameras(channel, camera, scene, topic):
    service = ArucoDetectorService(channel, MarkerDetector(DetectorOptions()), camera_ids=[1],
                                   queue_name=topic + ".Detector",
                                   frame_topic=topic + ".{}.Frame",
                                   detection_topic=topic + ".{}.Detection")
    camera(0, scene([(1, 50, 50)]), 1.0)
    camera(1, scene([(2, 50, 50)]), 2.0)
    time.sleep(0.2)

    (detection,) = service.step(timeout=1.0)

    assert detection.unpack(ObjectAnnotations).frame_id == 1
    with pytest.raises(socket.timeout):
        service.step(timeout=0.3)


@pytest.mark.parametrize("image", [Image(data=b"garbage"), Image()])
def test_an_undecodable_frame_publishes_nothing(service, camera, image):
    camera(0, image, 1.0)

    assert service.step(timeout=1.0) == []
    with pytest.raises(socket.timeout):
        camera.listener.consume(timeout=0.3)


def test_spans(service, camera, scene, topic, spans):
    camera(2, scene([(5, 50, 50)]), 1.0)
    service.step(timeout=1.0)
    camera(2, Image(data=b"garbage"), 2.0)
    service.step(timeout=1.0)

    finished = spans.get_finished_spans()
    ok, failed = [s for s in finished if s.name == "process {}.2.Frame".format(topic)]
    assert ok.kind == SpanKind.CONSUMER
    assert ok.attributes["pris.aruco_detector.camera_id"] == 2
    assert ok.attributes["pris.aruco_detector.markers"] == 1
    assert failed.status.status_code == SpanStatusCode.ERROR
    assert "pris.aruco_detector.markers" not in failed.attributes
    (publish,) = [s for s in finished if s.name == "publish {}.2.Detection".format(topic)]
    assert publish.parent.span_id == ok.context.span_id

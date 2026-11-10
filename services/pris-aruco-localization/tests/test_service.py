import socket
from pathlib import Path

import numpy as np
import pytest
from pris_msgs.camera_pb2 import FrameTransformations
from pris_msgs.image_pb2 import ObjectAnnotations
from pris_msgs.utils.io import load
from pris_msgs.utils.tensor import to_array
from pris_wire.core import Message, Subscription

from pris_aruco_localization.conf.options_pb2 import ArucoLocalizationOptions
from pris_aruco_localization.service import ArucoLocalization

DEFAULT_OPTIONS = Path(__file__).parents[1] / "etc" / "conf" / "options.json"


def annotations(scene, camera, markers, length=0.2):
    result = ObjectAnnotations(frame_id=camera.id)
    result.resolution.width, result.resolution.height = camera.width, camera.height
    for id, pose in markers.items():
        marker = result.objects.add(id=id, label=str(id), score=1.0)
        for x, y in scene.pixels(camera, pose, length):
            marker.region.vertices.add(x=float(x), y=float(y))
    return result


def localized(message):
    return {tf.source: tf for tf in message.unpack(FrameTransformations).tfs}


def make_options(markers=None, camera_ids=(0, 1, 2, 3), **fields):
    options = load(str(DEFAULT_OPTIONS), ArucoLocalizationOptions)
    if markers is not None:
        options.markers.clear()
        options.markers.update(markers)
    options.camera_ids[:] = camera_ids
    for name, value in fields.items():
        setattr(options, name, value)
    return options


@pytest.fixture
def localization(channel, connect, cameras, topic):
    publisher = connect()
    output = Subscription(publisher)
    output.subscribe(topic + ".FrameTransformations")

    def make(options=None, calibrated=None):
        options = options or make_options(markers={0: 0.2, 5: 0.2})
        known = calibrated if calibrated is not None else {c.id: c for c in cameras}
        service = ArucoLocalization(channel, known, options,
                                    detection_topic=topic + ".{}.Detection",
                                    transformations_topic=topic + ".FrameTransformations")

        def detect(scene, camera, markers, instant):
            message = Message(content=annotations(scene, camera, markers))
            message.created_at = instant
            publisher.publish(message, topic="{}.{}.Detection".format(topic, camera.id))

        service.detect = detect
        service.output = publisher
        return service

    return make


def test_default_options():
    options = load(str(DEFAULT_OPTIONS), ArucoLocalizationOptions)

    assert options.broker_uri == "amqp://guest:guest@rabbitmq.pris"
    assert options.reference_frame == 1000
    assert list(options.camera_ids) == [0, 1, 2, 3]
    assert dict(options.markers) == {0: pytest.approx(0.2)}
    assert options.telemetry.otlp_endpoint == "http://otel-collector.pris:4318"


def test_camera_id():
    assert ArucoLocalization.camera_id("ArUco.3.Detection") == 3
    assert ArucoLocalization.camera_id("ArUco.FrameTransformations") is None
    assert ArucoLocalization.camera_id("Lab.7.Markers", detection_topic="Lab.{}.Markers") == 7


def test_observations_keep_configured_markers_of_calibrated_cameras(cameras, scene):
    pose = scene.marker_pose(0.0, 0.0, 0.5)
    detections = {camera.id: annotations(scene, camera, {0: pose, 9: pose}) for camera in cameras}
    detections[2].objects[0].region.vertices.pop()

    calibrated = {c.id: c for c in cameras if c.id != 3}
    by_marker = ArucoLocalization.observations(detections, calibrated, {0: 0.2})

    assert list(by_marker) == [0]
    assert [o.camera.id for o in by_marker[0]] == [0, 1]


def test_observations_follow_the_detection_resolution(cameras, scene):
    pose = scene.marker_pose(0.0, 0.0, 0.5)
    half = cameras[0].scaled(cameras[0].width // 2, cameras[0].height // 2)

    (observation,) = ArucoLocalization.observations(
        {0: annotations(scene, half, {0: pose})}, {0: cameras[0]}, {0: 0.2})[0]

    assert observation.camera.width == half.width
    np.testing.assert_allclose(observation.camera.intrinsic, half.intrinsic)


def test_localizes_markers_seen_by_every_camera(localization, cameras, scene, spans):
    service = localization()
    marker0 = scene.marker_pose(0.3, -0.2, 0.4, 0.2, 0.1, 0.5)
    marker5 = scene.marker_pose(-0.5, 0.4, 0.0, 0.0, 0.0, 2.0)
    for camera in cameras:
        service.detect(scene, camera, {0: marker0, 5: marker5}, 50.0 + camera.id / 1000)

    message = service.step(timeout=2.0)

    assert message.created_at == pytest.approx(50.0015)
    received = service.output.consume(timeout=1.0)
    tfs = localized(received)
    assert sorted(tfs) == [100, 105]
    for frame, pose in ((100, marker0), (105, marker5)):
        assert tfs[frame].target == 1000
        np.testing.assert_allclose(to_array(tfs[frame].tf), pose, atol=1e-6)
        assert tfs[frame].expiration.ToNanoseconds() == pytest.approx(51.0015e9, abs=1e3)
    (span,) = [s for s in spans.get_finished_spans() if s.name == "localize"]
    assert span.attributes["pris.aruco_localization.cameras"] == (0, 1, 2, 3)
    assert span.attributes["pris.aruco_localization.markers"] == (0, 5)
    events = {e.attributes["pris.aruco_localization.marker_id"]: e for e in span.events}
    assert events[0].attributes["pris.aruco_localization.cameras"] == (0, 1, 2, 3)
    assert events[0].attributes["pris.aruco_localization.error"] < 1e-3
    assert len(span.links) == 4


def test_an_instant_comes_out_without_a_missing_camera(localization, cameras, scene):
    service = localization(make_options(markers={0: 0.2}))
    pose = scene.marker_pose(0.0, 0.0, 0.5)
    for camera in cameras[:3]:
        service.detect(scene, camera, {0: pose}, 20.0)

    message = service.step(timeout=2.0)

    assert sorted(localized(message)) == [100]


def test_empty_detections_publish_empty_transformations(localization, cameras, scene):
    service = localization(make_options(camera_ids=(0,)))
    service.detect(scene, cameras[0], {}, 7.0)

    message = service.step(timeout=2.0)

    assert localized(message) == {}
    assert message.created_at == pytest.approx(7.0)


def test_thresholds_discard_poses(localization, cameras, scene):
    service = localization(make_options(markers={0: 0.2}, camera_ids=(0,), min_cameras=2))
    service.detect(scene, cameras[0], {0: scene.marker_pose(0.0, 0.0, 0.5)}, 8.0)

    assert localized(service.step(timeout=2.0)) == {}


def test_cameras_without_calibration_are_skipped(localization, cameras, scene):
    service = localization(make_options(markers={0: 0.2}, camera_ids=(2,)), calibrated={})
    service.detect(scene, cameras[2], {0: scene.marker_pose(0.0, 0.0, 0.5)}, 9.0)

    assert localized(service.step(timeout=2.0)) == {}


def test_no_detections_time_out(localization):
    service = localization()

    with pytest.raises(socket.timeout):
        service.step(timeout=0.3)

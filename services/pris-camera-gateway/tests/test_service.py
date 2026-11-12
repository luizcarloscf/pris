import time

import pytest
from conftest import DEFAULT_OPTIONS
from google.protobuf.empty_pb2 import Empty
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.wrappers_pb2 import FloatValue
from pris_msgs.camera_pb2 import CameraConfig, CameraConfigFields
from pris_msgs.common_pb2 import FieldSelector
from pris_msgs.image_pb2 import Image, ImageFormats
from pris_msgs.utils.io import load
from pris_wire.core import Message, StatusCode, Subscription

from pris_camera_gateway import main
from pris_camera_gateway.conf.options_pb2 import CameraGatewayOptions, TriggerMode
from pris_camera_gateway.service import CameraGateway


@pytest.fixture
def gateway(channel, connect, make_camera, prefix):
    """A gateway on a fake camera, with a client channel listening to its topics."""
    def make(**fields):
        camera, fake = make_camera(**fields)
        service = CameraGateway(channel, camera, camera.options, prefix=prefix)
        status = service.set_config(camera.options.initial_config)
        assert status == Empty()
        camera.start()
        client = connect()
        frames = Subscription(client)
        frames.subscribe(f"{prefix}.0.Frame")
        frames.subscribe(f"{prefix}.0.Timestamp")
        service.client, service.fake = client, fake
        return service
    return make


def request(service, method, content):
    replies = Subscription(service.client)
    service.client.publish(Message(content=content, reply_to=replies),
                           topic=f"{service.frame_topic.rsplit('.', 1)[0]}.{method}")
    time.sleep(0.2)


def test_default_options():
    options = load(str(DEFAULT_OPTIONS), CameraGatewayOptions)

    assert options.broker_uri == "amqp://guest:guest@rabbitmq.pris"
    assert options.telemetry.otlp_endpoint == "http://otel-collector.pris:4318"
    assert options.camera.ip == "10.20.6.0"
    assert options.camera.trigger_mode == TriggerMode.FREE_RUN
    assert options.camera.initial_config.sampling.frequency.value == pytest.approx(10.0)


def test_free_run_publishes_the_frame_and_its_instant(gateway):
    service = gateway()

    capture = service.step()

    by_topic = {}
    for _ in range(2):
        message = service.client.consume(timeout=2.0)
        by_topic[message.topic.rsplit(".", 1)[1]] = message
    assert by_topic["Frame"].unpack(Image).data == capture.image.data
    stamp = by_topic["Timestamp"].unpack(Timestamp).ToNanoseconds()
    assert stamp == capture.timestamp_ns
    assert by_topic["Frame"].created_at == pytest.approx(capture.timestamp_ns / 1e9, abs=1e-3)


def test_requests_are_served_between_frames(gateway):
    service = gateway()
    config = CameraConfig()
    config.image.format.format = ImageFormats.PNG
    config.image.format.compression.value = 0.5
    request(service, "SetConfig", config)

    service.step()
    reply = service.client.consume(timeout=2.0)
    while reply.topic in (service.frame_topic, service.timestamp_topic):
        reply = service.client.consume(timeout=2.0)

    assert reply.status.code == StatusCode.OK
    assert service.camera.get_format().format == ImageFormats.PNG
    assert service.step().image.data.startswith(b"\x89PNG")


def test_scheduled_triggers_on_the_ticks(gateway):
    service = gateway(trigger_mode=TriggerMode.SOFTWARE_SCHEDULED)
    service.camera.set_sampling_rate(FloatValue(value=50.0))
    service.camera.set_delay(FloatValue(value=0.004))
    triggers = []
    service.fake.node_map.on_execute["TriggerSoftware"] = lambda: triggers.append(time.time_ns())

    for _ in range(3):
        service.step()

    assert len(triggers) == 3
    for trigger_ns in triggers:
        assert (trigger_ns - 4_000_000) % 20_000_000 < 2_000_000


def test_scheduled_serves_requests_while_waiting(gateway):
    service = gateway(trigger_mode=TriggerMode.SOFTWARE_SCHEDULED)
    service.camera.set_sampling_rate(FloatValue(value=5.0))
    request(service, "GetConfig", FieldSelector(fields=[CameraConfigFields.SAMPLING_SETTINGS]))

    started = time.time()
    service.serve_until_tick()

    reply = service.client.consume(timeout=1.0)
    assert reply.unpack(CameraConfig).sampling.frequency.value == pytest.approx(5.0)
    assert time.time() - started < 0.21


def test_get_config_leaves_out_what_the_camera_cant_read(gateway):
    service = gateway()
    service.fake.node_map.missing.add("GainAuto")

    config = service.get_config(FieldSelector(fields=[CameraConfigFields.ALL]))

    assert config.sampling.frequency.value == pytest.approx(10.0)
    assert config.image.format.format == ImageFormats.JPEG
    assert config.camera.HasField("shutter")
    assert not config.camera.HasField("gain")


def test_set_config_refuses_unsupported_settings_before_applying(gateway):
    service = gateway()
    config = CameraConfig()
    config.image.format.format = ImageFormats.PNG
    config.image.format.compression.value = 0.5
    config.camera.zoom.ratio = 0.5

    status = service.set_config(config)

    assert status.code == StatusCode.UNIMPLEMENTED
    assert service.camera.get_format().format == ImageFormats.JPEG


def test_set_config_returns_the_refused_setting(gateway):
    service = gateway()
    config = CameraConfig()
    config.sampling.delay.value = 0.01

    assert service.set_config(config).code == StatusCode.FAILED_PRECONDITION


def test_main_exits_on_unreadable_options(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.argv", ["pris-camera-gateway", str(tmp_path / "missing.json")])

    with pytest.raises(SystemExit):
        main.main()

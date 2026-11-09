from pathlib import Path

from opentelemetry.trace import SpanKind, StatusCode as SpanStatusCode
from pris_msgs.camera_pb2 import CameraCalibration, GetCalibrationReply, GetCalibrationRequest
from pris_msgs.utils.io import load
from pris_wire.core import Message, StatusCode, Subscription

from pris_calibration_server.conf.options_pb2 import CalibrationServerOptions
from pris_calibration_server.server import CalibrationServer

DEFAULT_OPTIONS = Path(__file__).parents[1] / "etc" / "conf" / "options.json"
CALIBRATIONS = {0: CameraCalibration(id=0), 3: CameraCalibration(id=3, error=0.5)}


def call(channel, *ids):
    server = CalibrationServer(channel, CALIBRATIONS)
    replies = Subscription(channel)
    channel.publish(Message(content=GetCalibrationRequest(ids=ids), reply_to=replies),
                    topic=server.topic)
    server.provider.serve(channel.consume(timeout=1.0))
    return channel.consume(timeout=1.0)


def server_span(spans):
    (span,) = [span for span in spans.get_finished_spans() if span.kind == SpanKind.SERVER]
    return span


def test_default_options():
    options = load(str(DEFAULT_OPTIONS), CalibrationServerOptions)

    assert options.broker_uri == "amqp://guest:guest@rabbitmq.pris"
    assert options.calibrations_path == "/etc/calibrations"
    assert options.telemetry.otlp_endpoint == "http://otel-collector.pris:4318"


def test_calibrations_in_the_order_requested(channel):
    reply = call(channel, 3, 0)

    assert reply.status.code == StatusCode.OK
    assert list(reply.unpack(GetCalibrationReply).calibrations) == [CALIBRATIONS[3],
                                                                    CALIBRATIONS[0]]


def test_no_ids_no_calibrations(channel):
    server = CalibrationServer(channel, CALIBRATIONS)

    assert server.get_calibrations(GetCalibrationRequest(), context=None) == GetCalibrationReply()


def test_unknown_camera_is_not_found(channel):
    reply = call(channel, 0, 99)

    assert reply.status.code == StatusCode.NOT_FOUND
    assert "'99'" in reply.status.why


def test_server_span_has_the_ids(channel, spans):
    call(channel, 0)

    span = server_span(spans)
    assert span.name == "CalibrationServer.GetCalibration"
    assert span.attributes["pris.calibration_server.ids"] == (0,)
    assert span.attributes["rpc.response.status_code"] == "OK"


def test_not_found_is_not_a_server_error(channel, spans):
    call(channel, 0, 7)

    span = server_span(spans)
    assert span.attributes["rpc.response.status_code"] == "NOT_FOUND"
    assert span.status.status_code == SpanStatusCode.UNSET

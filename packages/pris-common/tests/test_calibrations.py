import pytest
from pris_msgs.camera_pb2 import CameraCalibration, GetCalibrationReply, GetCalibrationRequest
from pris_wire.core import Status, StatusCode

from pris_common.calibrations import fetch_calibrations

KNOWN = {2: CameraCalibration(id=2, error=0.5), 3: CameraCalibration(id=3)}
UNKNOWN = 7


def get_calibration(request, context):
    if UNKNOWN in request.ids:
        return Status(StatusCode.NOT_FOUND, "unknown camera")
    return GetCalibrationReply(calibrations=[KNOWN[id] for id in request.ids if id in KNOWN])


@pytest.fixture
def server(serve, topic):
    serve(topic, get_calibration, GetCalibrationRequest, GetCalibrationReply)


def test_every_camera_known(channel, topic, server):
    assert fetch_calibrations(channel, [3, 2], topic=topic) == KNOWN


def test_an_unknown_camera_is_an_error(channel, topic, server):
    with pytest.raises(RuntimeError, match="NOT_FOUND"):
        fetch_calibrations(channel, [2, UNKNOWN], topic=topic)


def test_a_reply_missing_a_camera_is_an_error(channel, topic, server):
    with pytest.raises(RuntimeError, match=r"\[9\]"):
        fetch_calibrations(channel, [2, 9], topic=topic)

"""Camera calibrations fetched from pris-calibration-server."""

from __future__ import annotations

from collections.abc import Iterable

from pris_msgs.camera_pb2 import CameraCalibration, GetCalibrationReply, GetCalibrationRequest
from pris_wire.core import Channel

from pris_common.rpc import call


def fetch_calibrations(
    channel: Channel,
    camera_ids: Iterable[int],
    timeout: float = 5.0,
    topic: str = "CalibrationServer.GetCalibration",
) -> dict[int, CameraCalibration]:
    """Request the calibrations of the cameras and wait for the reply.

    Call it at startup, before subscribing to anything else on `channel`: it consumes the channel
    until the reply arrives, and drops any other message.

    Args:
        channel: the channel that publishes the request and consumes the reply.
        camera_ids: the cameras.
        timeout: the most seconds to wait for the reply.
        topic: where the calibration server listens.

    Returns:
        The calibrations, by camera id.

    Raises:
        socket.timeout: no reply within `timeout`.
        RuntimeError: the server answered with an error, such as NOT_FOUND for an unknown camera,
            or the reply misses a camera.
    """
    ids = sorted(set(camera_ids))
    reply = call(channel, GetCalibrationRequest(ids=ids), topic, timeout)
    calibrations = {c.id: c for c in reply.unpack(GetCalibrationReply).calibrations}
    missing = [id for id in ids if id not in calibrations]
    if missing:
        raise RuntimeError("no calibration for cameras {}".format(missing))
    return {id: calibrations[id] for id in ids}

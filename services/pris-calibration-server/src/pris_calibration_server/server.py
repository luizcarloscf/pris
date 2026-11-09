"""The RPC server: the calibrations kept in memory, served on CalibrationServer.GetCalibration."""

from __future__ import annotations

from opentelemetry import trace
from pris_msgs.camera_pb2 import CameraCalibration, GetCalibrationReply, GetCalibrationRequest
from pris_wire.core import Channel, Status, StatusCode
from pris_wire.rpc import LogInterceptor, ServiceProvider
from pris_wire.rpc.context import Context


class CalibrationServer(object):
    """Serves calibrations kept in memory."""

    def __init__(self, channel: Channel, calibrations: dict[int, CameraCalibration],
                 topic: str = "CalibrationServer.GetCalibration") -> None:
        """Register the request on `channel`; nothing is served before `run` or `serve`.

        Args:
            channel: the channel that consumes the requests and publishes the replies.
            calibrations: the calibrations, by camera id.
            topic: where the request is served.
        """
        self.calibrations = calibrations
        self.topic = topic
        self.provider = ServiceProvider(channel)
        self.provider.add_interceptor(LogInterceptor())
        self.provider.delegate(topic, self.get_calibrations,
                               GetCalibrationRequest, GetCalibrationReply)

    def run(self) -> None:
        """Serve requests until the process stops."""
        self.provider.run()

    def get_calibrations(self, request: GetCalibrationRequest,
                         context: Context) -> GetCalibrationReply | Status:
        """Return the calibrations of the requested cameras, in their order.

        Args:
            request: the camera ids.
            context: the request's context.

        Returns:
            The calibrations, or NOT_FOUND for the first unknown id.
        """
        trace.get_current_span().set_attribute("pris.calibration_server.ids", list(request.ids))
        reply = GetCalibrationReply()
        for id in request.ids:
            if id not in self.calibrations:
                return Status(StatusCode.NOT_FOUND,
                              "CameraCalibration with id '{}' not found".format(id))
            reply.calibrations.add().CopyFrom(self.calibrations[id])
        return reply

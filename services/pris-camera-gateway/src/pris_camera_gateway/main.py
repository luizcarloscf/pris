"""The entry point: load the options, connect to the camera, then publish its frames."""

from __future__ import annotations

import signal
import sys
from types import FrameType

from google.protobuf.json_format import ParseError
from opentelemetry.instrumentation.pris_wire.otlp import setup_telemetry
from pris_msgs.utils.io import load
from pris_wire.core import Channel, Logger

from pris_camera_gateway.camera import SpinnakerCamera
from pris_camera_gateway.conf.options_pb2 import CameraGatewayOptions
from pris_camera_gateway.nodes import StatusException
from pris_camera_gateway.service import CameraGateway

DEFAULT_OPTIONS_PATH = "/etc/pris-camera-gateway/options.json"
SERVICE_NAME = "pris-camera-gateway"


def main() -> None:
    """Run the gateway with the options file given as argument, or the default one."""
    logger = Logger(name="CameraGateway", level=Logger.INFO, propagate=False)
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OPTIONS_PATH
    try:
        options = load(path, CameraGatewayOptions)
    except (OSError, ValueError, ParseError) as error:
        logger.critical("unable to load '{}': {}", path, error)
    logger.info("CameraGatewayOptions: \n{}", options)

    shutdown_telemetry = setup_telemetry(
        options.telemetry.otlp_endpoint,
        options.telemetry.service_name,
        default_service_name=SERVICE_NAME,
    )
    signal.signal(signal.SIGTERM, _exit_on_sigterm)
    try:
        camera = SpinnakerCamera(options.camera)
        try:
            camera.connect()
        except (RuntimeError, StatusException) as error:
            logger.critical("unable to connect to the camera: {}", error)
        channel = Channel(uri=options.broker_uri)
        CameraGateway(channel, camera, options.camera).run()
    finally:
        shutdown_telemetry()


def _exit_on_sigterm(signum: int, frame: FrameType | None) -> None:
    sys.exit(0)


if __name__ == "__main__":
    main()

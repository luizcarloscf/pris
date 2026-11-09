"""The entry point: load the options, fetch the calibrations, then serve."""

from __future__ import annotations

import signal
import socket
import sys
from types import FrameType

from google.protobuf.json_format import ParseError
from opentelemetry.instrumentation.pris_wire.otlp import setup_telemetry
from pris_common.calibrations import fetch_calibrations
from pris_msgs.utils.io import load
from pris_wire.core import Channel, Logger

from pris_frame_transformation.conf.options_pb2 import FrameTransformationOptions
from pris_frame_transformation.service import FrameTransformationService

DEFAULT_OPTIONS_PATH = "/etc/pris-frame-transformation/options.json"
SERVICE_NAME = "pris-frame-transformation"


def main() -> None:
    """Run the service with the options file given as argument, or the default one."""
    logger = Logger(name="FrameTransformation", level=Logger.INFO, propagate=False)
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OPTIONS_PATH
    try:
        options = load(path, FrameTransformationOptions)
    except (OSError, ValueError, ParseError) as error:
        logger.critical("unable to load '{}': {}", path, error)
    logger.info("FrameTransformationOptions: \n{}", options)

    shutdown_telemetry = setup_telemetry(
        options.telemetry.otlp_endpoint,
        options.telemetry.service_name,
        default_service_name=SERVICE_NAME,
    )
    signal.signal(signal.SIGTERM, _exit_on_sigterm)
    try:
        channel = Channel(uri=options.broker_uri)
        try:
            calibrations = fetch_calibrations(channel, options.camera_ids)
            service = FrameTransformationService(channel, calibrations.values())
        except (socket.timeout, RuntimeError, ValueError) as error:
            logger.critical("unable to use the calibrations: {}", error)
        service.run()
    finally:
        shutdown_telemetry()


def _exit_on_sigterm(signum: int, frame: FrameType | None) -> None:
    sys.exit(0)


if __name__ == "__main__":
    main()

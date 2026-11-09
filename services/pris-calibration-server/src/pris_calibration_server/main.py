"""The entry point: load the options and the calibrations, then serve."""

from __future__ import annotations

import signal
import sys
from types import FrameType

from google.protobuf.json_format import ParseError
from opentelemetry.instrumentation.pris_wire.otlp import setup_telemetry
from pris_msgs.utils.io import load
from pris_wire.core import Channel, Logger

from pris_calibration_server.calibration import load_calibrations
from pris_calibration_server.conf.options_pb2 import CalibrationServerOptions
from pris_calibration_server.server import CalibrationServer

DEFAULT_OPTIONS_PATH = "/etc/pris-calibration-server/options.json"
SERVICE_NAME = "pris-calibration-server"


def main() -> None:
    """Run the server with the options file given as argument, or the default one."""
    logger = Logger(name="CalibrationServer", level=Logger.INFO, propagate=False)
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OPTIONS_PATH
    try:
        options = load(path, CalibrationServerOptions)
    except (OSError, ValueError, ParseError) as error:
        logger.critical("unable to load '{}': {}", path, error)
    logger.info("CalibrationServerOptions: \n{}", options)

    try:
        calibrations = load_calibrations(options.calibrations_path)
    except (OSError, ValueError, ParseError) as error:
        logger.critical("unable to load the calibrations: {}", error)
    for id, calibration in sorted(calibrations.items()):
        logger.info("Calibration id={} calibrated_at={}",
                    id, calibration.calibrated_at.ToJsonString())

    shutdown_telemetry = setup_telemetry(
        options.telemetry.otlp_endpoint,
        options.telemetry.service_name,
        default_service_name=SERVICE_NAME,
    )
    signal.signal(signal.SIGTERM, _exit_on_sigterm)
    try:
        CalibrationServer(Channel(uri=options.broker_uri), calibrations).run()
    finally:
        shutdown_telemetry()


def _exit_on_sigterm(signum: int, frame: FrameType | None) -> None:
    sys.exit(0)


if __name__ == "__main__":
    main()

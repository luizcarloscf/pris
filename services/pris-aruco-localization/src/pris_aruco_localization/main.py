"""The entry point: load the options, fetch the calibrations, then localize."""

from __future__ import annotations

import signal
import socket
import sys
from types import FrameType

from google.protobuf.json_format import ParseError
from opentelemetry.instrumentation.pris_wire.otlp import setup_telemetry
from pris_common.calibrations import fetch_calibrations
from pris_common.transformations import fetch_transformations
from pris_msgs.utils.io import load
from pris_wire.core import Channel, Logger

from pris_aruco_localization.conf.options_pb2 import ArucoLocalizationOptions
from pris_aruco_localization.geometry import camera_from_calibration, extrinsic_from
from pris_aruco_localization.service import ArucoLocalization

DEFAULT_OPTIONS_PATH = "/etc/pris-aruco-localization/options.json"
SERVICE_NAME = "pris-aruco-localization"


def main() -> None:
    """Run the service with the options file given as argument, or the default one."""
    logger = Logger(name="ArucoLocalization", level=Logger.INFO, propagate=False)
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OPTIONS_PATH
    try:
        options = load(path, ArucoLocalizationOptions)
    except (OSError, ValueError, ParseError) as error:
        logger.critical("unable to load '{}': {}", path, error)
    logger.info("ArucoLocalizationOptions: \n{}", options)

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
            missing = [(options.reference_frame, id) for id, calibration in calibrations.items()
                       if extrinsic_from(calibration, options.reference_frame) is None]
            composed = fetch_transformations(channel, missing) if missing else {}
            for source, target in missing:
                logger.info("Camera {}: extrinsic from {} composed by the frame graph", target,
                            source)
            cameras = {id: camera_from_calibration(calibration, options.reference_frame,
                                                   composed.get((options.reference_frame, id)))
                       for id, calibration in calibrations.items()}
        except (socket.timeout, RuntimeError, ValueError) as error:
            logger.critical("unable to use the calibrations: {}", error)
        ArucoLocalization(channel, cameras, options).run()
    finally:
        shutdown_telemetry()


def _exit_on_sigterm(signum: int, frame: FrameType | None) -> None:
    sys.exit(0)


if __name__ == "__main__":
    main()

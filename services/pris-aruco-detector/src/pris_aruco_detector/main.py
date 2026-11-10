"""The entry point: load the options, create the detector, then serve."""

from __future__ import annotations

import signal
import sys
from types import FrameType

import cv2
from google.protobuf.json_format import ParseError
from opentelemetry.instrumentation.pris_wire.otlp import setup_telemetry
from pris_msgs.utils.io import load
from pris_wire.core import Channel, Logger

from pris_aruco_detector.conf.options_pb2 import ArucoDetectorOptions
from pris_aruco_detector.detector import MarkerDetector
from pris_aruco_detector.service import ArucoDetectorService

DEFAULT_OPTIONS_PATH = "/etc/pris-aruco-detector/options.json"
SERVICE_NAME = "pris-aruco-detector"


def main() -> None:
    """Run the service with the options file given as argument, or the default one."""
    logger = Logger(name="ArucoDetector", level=Logger.INFO, propagate=False)
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OPTIONS_PATH
    try:
        options = load(path, ArucoDetectorOptions)
    except (OSError, ValueError, ParseError) as error:
        logger.critical("unable to load '{}': {}", path, error)
    logger.info("ArucoDetectorOptions: \n{}", options)

    if options.detector.cpu_threads > 0:
        cv2.setNumThreads(options.detector.cpu_threads)
    detector = MarkerDetector(options.detector)

    shutdown_telemetry = setup_telemetry(
        options.telemetry.otlp_endpoint,
        options.telemetry.service_name,
        default_service_name=SERVICE_NAME,
    )
    signal.signal(signal.SIGTERM, _exit_on_sigterm)
    try:
        channel = Channel(uri=options.broker_uri)
        ArucoDetectorService(channel, detector, options.camera_ids, options.queue_name).run()
    finally:
        shutdown_telemetry()


def _exit_on_sigterm(signum: int, frame: FrameType | None) -> None:
    sys.exit(0)


if __name__ == "__main__":
    main()

"""The entry point: load the options, get the bindings, then follow the events."""

from __future__ import annotations

import signal
import sys
from types import FrameType

import requests
from google.protobuf.json_format import ParseError
from opentelemetry.instrumentation.pris_wire.otlp import setup_telemetry
from pris_msgs.utils.io import load
from pris_wire.core import Channel, Logger

from pris_broker_events.conf.options_pb2 import BrokerEventsOptions
from pris_broker_events.management import fetch_bindings
from pris_broker_events.service import BrokerEvents

DEFAULT_OPTIONS_PATH = "/etc/pris-broker-events/options.json"
SERVICE_NAME = "pris-broker-events"


def main() -> None:
    """Run the service with the options file given as argument, or the default one."""
    logger = Logger(name="BrokerEvents", level=Logger.INFO, propagate=False)
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OPTIONS_PATH
    try:
        options = load(path, BrokerEventsOptions)
    except (OSError, ValueError, ParseError) as error:
        logger.critical("unable to load '{}': {}", path, error)
    logger.info("BrokerEventsOptions: \n{}", options)

    shutdown_telemetry = setup_telemetry(
        options.telemetry.otlp_endpoint,
        options.telemetry.service_name,
        default_service_name=SERVICE_NAME,
    )
    signal.signal(signal.SIGTERM, _exit_on_sigterm)
    try:
        service = BrokerEvents(Channel(uri=options.broker_uri))
        api = options.broker_management_api
        try:
            service.load(fetch_bindings(api.uri, api.timeout))
        except requests.RequestException as error:
            logger.critical("unable to get the bindings: {}", error)
        service.run()
    finally:
        shutdown_telemetry()


def _exit_on_sigterm(signum: int, frame: FrameType | None) -> None:
    sys.exit(0)


if __name__ == "__main__":
    main()

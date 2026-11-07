from __future__ import annotations

import logging
import os
from sys import exit
from typing import Any, NoReturn

from colorlog import ColoredFormatter, StreamHandler, getLogger

from .utils import assert_type

LOG_LEVEL_ENV = "LOG_LEVEL"


def _level_from_env() -> int | None:
    name = os.environ.get(LOG_LEVEL_ENV, "").strip().upper()
    if not name:
        return None
    level = logging.getLevelName(name)
    if isinstance(level, int):
        return level
    logging.getLogger(__name__).warning(
        "Ignoring invalid %s=%r", LOG_LEVEL_ENV, os.environ[LOG_LEVEL_ENV])
    return None


class Logger:
    """A colored logger whose methods format their message with str.format."""

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARN = logging.WARN
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

    def __init__(self, name: str, level: int | str = logging.DEBUG,
                 propagate: bool = True) -> None:
        """Create or reuse the logger `name`.

        Args:
            name: the logger's name, shown in every line.
            level: the default level; the LOG_LEVEL environment variable (e.g. LOG_LEVEL=INFO)
                overrides it when it names a valid level.
            propagate: also pass records to the parent loggers; set it to False when the root
                logger has handlers too (e.g. logging.basicConfig), to avoid printing lines twice.

        Raises:
            TypeError: `name` isn't a str.
        """
        assert_type(name, str, "name")

        style = "%(log_color)s[%(levelname)-.1s][%(threadName)s]" \
                "[%(asctime)s][%(name)s] %(message)s"

        formatter = ColoredFormatter(
            style,
            datefmt=None,
            reset=True,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'white',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'white,bg_red',
            },
            secondary_log_colors={},
            style='%',
        )

        self.logger = getLogger(name)
        if len(self.logger.handlers) == 0 and name:
            handler = StreamHandler()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        env_level = _level_from_env()
        self.set_level(level if env_level is None else env_level)
        self.logger.propagate = propagate

    def set_level(self, level: int | str) -> None:
        """Set the lowest level logged.

        Args:
            level: a level, such as Logger.INFO or "INFO".
        """
        self.logger.setLevel(level)

    def debug(self, formatter: str, *args: Any) -> None:
        """Log `formatter.format(*args)` at DEBUG level."""
        self.logger.debug(formatter.format(*args))

    def info(self, formatter: str, *args: Any) -> None:
        """Log `formatter.format(*args)` at INFO level."""
        self.logger.info(formatter.format(*args))

    def warn(self, formatter: str, *args: Any) -> None:
        """Log `formatter.format(*args)` at WARNING level."""
        self.logger.warning(formatter.format(*args))

    def error(self, formatter: str, *args: Any) -> None:
        """Log `formatter.format(*args)` at ERROR level."""
        self.logger.error(formatter.format(*args))

    def critical(self, formatter: str, *args: Any) -> NoReturn:
        """Log `formatter.format(*args)` at CRITICAL level, then exit the process with -1."""
        self.logger.critical(formatter.format(*args))
        exit(-1)

import logging

import pytest
from pris_wire.core import Logger


@pytest.fixture(autouse=True)
def no_log_level(monkeypatch):
    monkeypatch.delenv("LOG_LEVEL", raising=False)


def test_default_level_is_debug():
    assert Logger("test.default").logger.level == logging.DEBUG


def test_level_argument():
    assert Logger("test.argument", Logger.INFO).logger.level == logging.INFO
    assert Logger("test.argument.str", "WARNING").logger.level == logging.WARNING


def test_log_level_env_overrides_argument(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "error")
    assert Logger("test.env", Logger.DEBUG).logger.level == logging.ERROR


def test_invalid_log_level_env_is_ignored(monkeypatch, caplog):
    monkeypatch.setenv("LOG_LEVEL", "LOUD")
    assert Logger("test.invalid", Logger.INFO).logger.level == logging.INFO
    assert "Ignoring invalid LOG_LEVEL='LOUD'" in caplog.text


def test_level_applies_to_existing_logger():
    Logger("test.same", Logger.DEBUG)
    assert Logger("test.same", Logger.ERROR).logger.level == logging.ERROR


def test_single_handler_per_name():
    Logger("test.handlers")
    assert len(Logger("test.handlers").logger.handlers) == 1


def test_propagate():
    assert Logger("test.propagate").logger.propagate is True
    assert Logger("test.quiet", propagate=False).logger.propagate is False


def test_critical_exits():
    with pytest.raises(SystemExit):
        Logger("test.critical").critical("fatal {}", 1)

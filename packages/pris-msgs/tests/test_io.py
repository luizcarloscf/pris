import pytest
from google.protobuf.json_format import ParseError

from pris_msgs.common_pb2 import SamplingSettings
from pris_msgs.utils.io import load, save


def write(tmp_path, text):
    path = tmp_path / "options.json"
    path.write_text(text)
    return str(path)


def test_load(tmp_path):
    path = write(tmp_path, '{"frequency": 10.0, "delay": 0.25}')
    options = load(path, SamplingSettings)
    assert isinstance(options, SamplingSettings)
    assert options.frequency.value == 10.0
    assert options.delay.value == 0.25


@pytest.mark.parametrize("text", [
    '{"frequency": 10.0, "unknown": 1}',
    '{"frequency": ',
    '{"frequency": "fast"}',
])
def test_load_invalid(tmp_path, text):
    path = write(tmp_path, text)
    with pytest.raises(ParseError):
        load(path, SamplingSettings)


def test_load_missing_file(tmp_path):
    path = str(tmp_path / "missing.json")
    with pytest.raises(FileNotFoundError, match="missing.json"):
        load(path, SamplingSettings)


def test_load_not_utf8(tmp_path):
    path = tmp_path / "options.json"
    path.write_bytes(b'{"frequency": "\xff"}')
    with pytest.raises(UnicodeDecodeError):
        load(str(path), SamplingSettings)


def test_save_then_load(tmp_path):
    path = str(tmp_path / "saved.json")
    options = load(write(tmp_path, '{"frequency": 10.0, "delay": 0.25}'), SamplingSettings)
    save(path, options)
    assert load(path, SamplingSettings) == options


def test_save_unwritable_path(tmp_path):
    path = str(tmp_path / "missing" / "saved.json")
    with pytest.raises(FileNotFoundError, match="saved.json"):
        save(path, SamplingSettings())

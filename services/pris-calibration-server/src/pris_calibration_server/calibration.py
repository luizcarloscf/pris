"""Calibration files: one CameraCalibration in protobuf JSON per camera, named `<id>.json`."""

from __future__ import annotations

from pathlib import Path

from pris_msgs.camera_pb2 import CameraCalibration
from pris_msgs.utils.io import load


def load_calibration(path: Path) -> CameraCalibration:
    """Load one calibration file, named after its camera id.

    Args:
        path: a `<id>.json` file.

    Returns:
        The calibration.

    Raises:
        OSError: the file can't be read.
        UnicodeDecodeError: the file isn't UTF-8.
        google.protobuf.json_format.ParseError: the file isn't JSON or has unknown fields.
        ValueError: the calibration's id isn't the file name.
    """
    calibration = load(str(path), CameraCalibration)
    if str(calibration.id) != path.stem:
        raise ValueError("calibration '{}' has id {}, expected the file name".format(
            path, calibration.id))
    return calibration


def load_calibrations(directory: str) -> dict[int, CameraCalibration]:
    """Load every `*.json` calibration of a directory; other files and subdirectories are ignored.

    Args:
        directory: the directory.

    Returns:
        The calibrations, by camera id.

    Raises:
        NotADirectoryError: `directory` isn't a directory.
        ValueError: `directory` holds no calibration.
        OSError, UnicodeDecodeError, google.protobuf.json_format.ParseError, ValueError: a
            calibration can't be loaded, as in `load_calibration`.
    """
    root = Path(directory)
    if not root.is_dir():
        raise NotADirectoryError("'{}' is not a directory".format(directory))
    calibrations = {}
    for path in sorted(root.glob("*.json")):
        calibration = load_calibration(path)
        calibrations[calibration.id] = calibration
    if not calibrations:
        raise ValueError("no '*.json' calibrations in '{}'".format(directory))
    return calibrations

import json
from pathlib import Path

import numpy as np
import pytest
from google.protobuf.json_format import MessageToDict, ParseError
from pris_msgs.camera_pb2 import CameraCalibration
from pris_msgs.utils.tensor import to_array

from pris_calibration_server.calibration import load_calibration, load_calibrations

CALIBRATIONS = Path(__file__).parents[3] / "calibrations"
SITES = sorted(path for path in CALIBRATIONS.iterdir() if path.is_dir())


def calibration(id, error=0.5):
    message = CameraCalibration(id=id, error=error)
    message.resolution.width = 1288
    message.resolution.height = 728
    return message


def write(directory, name, content):
    path = directory / name
    if isinstance(content, CameraCalibration):
        content = json.dumps(MessageToDict(content))
    path.write_text(content)
    return path


def test_load_calibrations(tmp_path):
    write(tmp_path, "0.json", calibration(0))
    write(tmp_path, "12.json", calibration(12, error=0.25))
    write(tmp_path, "README.md", "not a calibration")
    (tmp_path / "old").mkdir()
    write(tmp_path / "old", "3.json", calibration(3))

    calibrations = load_calibrations(str(tmp_path))

    assert calibrations == {0: calibration(0), 12: calibration(12, error=0.25)}


def test_id_must_match_file_name(tmp_path):
    path = write(tmp_path, "1.json", calibration(2))
    with pytest.raises(ValueError, match="has id 2"):
        load_calibration(path)


def test_missing_id_reads_as_zero(tmp_path):
    assert load_calibration(write(tmp_path, "0.json", "{}")).id == 0
    with pytest.raises(ValueError, match="has id 0"):
        load_calibration(write(tmp_path, "5.json", "{}"))


def test_invalid_json(tmp_path):
    write(tmp_path, "0.json", calibration(0))
    write(tmp_path, "1.json", '{"id": "1",')
    with pytest.raises(ParseError):
        load_calibrations(str(tmp_path))


def test_unknown_field(tmp_path):
    with pytest.raises(ParseError):
        load_calibration(write(tmp_path, "0.json", '{"id": "0", "focal": 1.0}'))


def test_unreadable_file(tmp_path):
    path = tmp_path / "0.json"
    path.mkdir()
    with pytest.raises(OSError):
        load_calibration(path)


def test_not_a_directory(tmp_path):
    with pytest.raises(NotADirectoryError):
        load_calibrations(str(tmp_path / "missing"))


def test_empty_directory(tmp_path):
    with pytest.raises(ValueError, match="no"):
        load_calibrations(str(tmp_path))


@pytest.mark.parametrize("site", SITES, ids=[site.name for site in SITES])
def test_repository_calibrations(site):
    calibrations = load_calibrations(str(site))
    for id, calib in calibrations.items():
        assert calib.resolution.width > 0 and calib.resolution.height > 0, id
        intrinsic = to_array(calib.intrinsic)
        assert intrinsic.shape == (3, 3), id
        assert intrinsic[0, 0] > 0 and intrinsic[1, 1] > 0 and intrinsic[2, 2] == 1, id
        assert to_array(calib.distortion).shape == (1, 5), id
        for extrinsic in calib.extrinsic:
            assert extrinsic.source != extrinsic.target, id
            assert extrinsic.target == id, id
            tf = to_array(extrinsic.tf)
            assert tf.shape == (4, 4), id
            np.testing.assert_allclose(tf[3], [0, 0, 0, 1], err_msg=str(id))
            rotation = tf[:3, :3]
            np.testing.assert_allclose(rotation @ rotation.T, np.eye(3), atol=1e-6,
                                       err_msg=str(id))
            assert np.linalg.det(rotation) == pytest.approx(1.0, abs=1e-6), id


def test_repository_has_calibrations():
    assert SITES, "no site under {}".format(CALIBRATIONS)

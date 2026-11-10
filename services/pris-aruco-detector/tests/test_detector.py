import cv2
import pytest
from pris_msgs.image_pb2 import Image

from pris_aruco_detector.conf.options_pb2 import (
    ArucoDictionary,
    CornerRefinement,
    DetectorOptions,
)
from pris_aruco_detector.detector import MarkerDetector, corner_refinement_id, dictionary_id

MARKER_SIZE = 120


def corners(annotation):
    return [(vertex.x, vertex.y) for vertex in annotation.region.vertices]


@pytest.mark.parametrize("extension", [".png", ".jpg"])
def test_detects_ids_and_corners(scene, extension):
    image = scene([(3, 100, 80), (7, 400, 250)], extension=extension, marker_size=MARKER_SIZE)
    annotations = MarkerDetector(DetectorOptions()).detect(image)

    assert (annotations.resolution.width, annotations.resolution.height) == (640, 480)
    by_id = {marker.id: marker for marker in annotations.objects}
    assert sorted(by_id) == [3, 7]
    assert by_id[3].label == "3"
    assert by_id[3].score == 1.0

    x, y, last = 100 - 0.5, 80 - 0.5, MARKER_SIZE
    expected = [(x, y), (x + last, y), (x + last, y + last), (x, y + last)]
    for (cx, cy), (ex, ey) in zip(corners(by_id[3]), expected):
        assert cx == pytest.approx(ex, abs=1.0)
        assert cy == pytest.approx(ey, abs=1.0)


def test_no_markers(scene):
    annotations = MarkerDetector(DetectorOptions()).detect(scene([]))
    assert len(annotations.objects) == 0
    assert annotations.resolution.width == 640


def test_other_dictionary_is_ignored(scene):
    image = scene([(3, 100, 80)], dictionary=cv2.aruco.DICT_6X6_50)

    assert len(MarkerDetector(DetectorOptions()).detect(image).objects) == 0
    options = DetectorOptions(dictionary=ArucoDictionary.DICT_6X6_50)
    assert [marker.id for marker in MarkerDetector(options).detect(image).objects] == [3]


@pytest.mark.parametrize("image, error", [
    (Image(), cv2.error),
    (Image(uri="http://camera/frame.jpg"), cv2.error),
    (Image(data=b"not an image"), ValueError),
])
def test_undecodable_images(image, error):
    with pytest.raises(error):
        MarkerDetector(DetectorOptions()).detect(image)


def test_every_dictionary_and_refinement_maps_to_opencv():
    for name, value in ArucoDictionary.items():
        assert dictionary_id(value) == getattr(cv2.aruco, name)
        cv2.aruco.getPredefinedDictionary(dictionary_id(value))
    for name, value in CornerRefinement.items():
        assert corner_refinement_id(value) == getattr(cv2.aruco, name)
    assert all(value == getattr(cv2.aruco, name) for name, value in ArucoDictionary.items())

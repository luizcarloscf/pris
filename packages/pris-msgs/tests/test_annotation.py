import numpy as np
import pytest

from pris_msgs.image_pb2 import HumanKeypoints as K
from pris_msgs.image_pb2 import ObjectAnnotation
from pris_msgs.utils.annotation import to_annotation, to_array

ORIGINAL = {
    "UNKNOWN_HUMAN_KEYPOINT": 0, "HEAD": 1, "NOSE": 2, "NECK": 3, "RIGHT_SHOULDER": 4,
    "RIGHT_ELBOW": 5, "RIGHT_WRIST": 6, "LEFT_SHOULDER": 7, "LEFT_ELBOW": 8, "LEFT_WRIST": 9,
    "RIGHT_HIP": 10, "RIGHT_KNEE": 11, "RIGHT_ANKLE": 12, "LEFT_HIP": 13, "LEFT_KNEE": 14,
    "LEFT_ANKLE": 15, "RIGHT_EYE": 16, "LEFT_EYE": 17, "RIGHT_EAR": 18, "LEFT_EAR": 19,
    "CHEST": 20,
}


def test_original_values_unchanged():
    assert {name: K.Value(name) for name in ORIGINAL} == ORIGINAL


def test_new_values_are_in_their_blocks():
    assert K.PELVIS == 21 and K.RIGHT_HEEL == 27
    assert K.Value("FACE_0") == 100 and K.Value("FACE_67") == 167
    assert K.LEFT_HAND_ROOT == 200 and K.LEFT_HAND_PINKY_4 == 220
    assert K.RIGHT_HAND_ROOT == 300 and K.RIGHT_HAND_PINKY_4 == 320


IDS = [K.NOSE, K.LEFT_EYE, K.RIGHT_EYE]


def test_round_trip_2d():
    points = np.array([[1.5, 2.5], [3.0, 4.0], [5.0, 6.0]])
    scores = np.array([0.5, 0.25, 0.75])
    annotation = to_annotation(points, scores, IDS, label="human_skeleton", id=7)
    assert (annotation.label, annotation.id, annotation.score) == ("human_skeleton", 7, 0.5)
    assert [keypoint.id for keypoint in annotation.keypoints] == IDS
    back, back_scores = to_array(annotation, IDS)
    assert back.shape == (3, 3)
    np.testing.assert_array_equal(back[:, :2], points)
    np.testing.assert_array_equal(back[:, 2], 0)
    np.testing.assert_array_equal(back_scores, scores)


def test_round_trip_3d():
    points = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
    scores = np.array([1.0, 0.5, 0.25])
    back, back_scores = to_array(to_annotation(points, scores, IDS), IDS)
    np.testing.assert_array_equal(back, points)
    np.testing.assert_array_equal(back_scores, scores)


def test_to_array_follows_the_keypoints_order():
    annotation = ObjectAnnotation()
    annotation.keypoints.add(id=K.LEFT_HAND_ROOT, score=0.5)
    keypoint = annotation.keypoints.add(id=K.RIGHT_EYE, score=0.75)
    keypoint.position.x, keypoint.position.y = 1.0, 2.0
    points, scores = to_array(annotation, IDS)
    assert np.isnan(points[:2]).all()
    np.testing.assert_array_equal(points[2], [1.0, 2.0, 0.0])
    np.testing.assert_array_equal(scores, [0, 0, 0.75])


def test_missing_and_low_scored_keypoints_are_left_out():
    points = np.array([[1.0, 2.0], [np.nan, np.nan], [5.0, 6.0]])
    scores = np.array([0.5, 0.75, 0.25])
    annotation = to_annotation(points, scores, IDS, threshold=0.3)
    assert [keypoint.id for keypoint in annotation.keypoints] == [K.NOSE]
    assert annotation.score == 0.5
    assert to_annotation(points, scores, IDS, threshold=0.9).score == 0.0


def test_score_and_box():
    annotation = to_annotation(np.zeros((3, 2)), np.ones(3), IDS, score=0.25,
                               box=[1.0, 2.0, 3.0, 4.0])
    assert annotation.score == 0.25
    assert [(v.x, v.y) for v in annotation.region.vertices] == [(1.0, 2.0), (3.0, 4.0)]


@pytest.mark.parametrize("points, scores, keypoints, error", [
    (np.zeros((3, 4)), np.zeros(3), IDS, ValueError),
    (np.zeros((3, 2)), np.zeros(2), IDS, ValueError),
    (np.zeros(3), np.zeros(3), IDS, IndexError),
    (np.zeros((3, 2)), np.zeros(3), IDS[:2], IndexError),
])
def test_to_annotation_shape_errors(points, scores, keypoints, error):
    with pytest.raises(error):
        to_annotation(points, scores, keypoints)

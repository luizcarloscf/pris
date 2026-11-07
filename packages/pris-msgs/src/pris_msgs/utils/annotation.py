"""Convert ObjectAnnotation keypoints to and from NumPy arrays. Needs pris-msgs[numpy]."""

from __future__ import annotations

from typing import Sequence, Tuple

try:
    import numpy as np
    import numpy.typing as npt
except ImportError as error:  # pragma: no cover
    raise ImportError(
        "pris_msgs.utils.annotation needs NumPy: install pris-msgs[numpy]"
    ) from error

from pris_msgs.image_pb2 import ObjectAnnotation


def to_array(
    annotation: ObjectAnnotation,
    keypoints: Sequence[int],
) -> Tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Convert an annotation's keypoints to arrays.

    Args:
        annotation: the annotation to read.
        keypoints: the HumanKeypoints ids to return, in order; other keypoints are ignored.

    Returns:
        points (K, 3) x, y, z, NaN for the keypoints the annotation lacks, and scores (K), 0 for
        those.
    """
    index = {int(id): position for position, id in enumerate(keypoints)}
    points = np.full((len(keypoints), 3), np.nan)
    scores = np.zeros(len(keypoints))
    for keypoint in annotation.keypoints:
        position = index.get(keypoint.id)
        if position is None:
            continue
        points[position] = keypoint.position.x, keypoint.position.y, keypoint.position.z
        scores[position] = keypoint.score
    return points, scores


def to_annotation(
    points: npt.ArrayLike,
    scores: npt.ArrayLike,
    keypoints: Sequence[int],
    label: str = "",
    id: int = 0,
    score: float | None = None,
    box: npt.ArrayLike | None = None,
    threshold: float = 0.0,
) -> ObjectAnnotation:
    """Convert keypoint arrays to an annotation.

    Args:
        points: (K, 2) or (K, 3) coordinates; keypoints with a NaN are left out.
        scores: (K) scores; keypoints below `threshold` are left out.
        keypoints: the K HumanKeypoints ids.
        label: the annotation's label.
        id: the annotation's id.
        score: the annotation's score; by default the mean of the kept keypoints' (0 if none).
        box: x1, y1, x2, y2, the region's top-left and bottom-right corners.
        threshold: the lowest score kept.

    Returns:
        A new annotation with the kept keypoints.

    Raises:
        ValueError: `points` has neither 2 nor 3 columns, or `scores` doesn't have K values.
        IndexError: `points` isn't 2-D, or `keypoints` doesn't have K ids.
    """
    points = np.asarray(points, dtype=np.float64)
    scores = np.asarray(scores, dtype=np.float64)
    ids = np.asarray(keypoints)
    if points.shape[1] not in (2, 3):
        raise ValueError(f"points of shape {points.shape}, expected (K, 2) or (K, 3)")

    kept = np.isfinite(points).all(axis=1) & (scores >= threshold)
    if score is None:
        score = float(scores[kept].mean()) if kept.any() else 0.0
    annotation = ObjectAnnotation(label=label, id=id, score=score)
    if box is not None:
        x1, y1, x2, y2 = np.asarray(box, dtype=np.float64).tolist()
        annotation.region.vertices.add(x=x1, y=y1)
        annotation.region.vertices.add(x=x2, y=y2)
    for keypoint_id, point, keypoint_score in zip(
        ids[kept].tolist(), points[kept].tolist(), scores[kept].tolist()
    ):
        keypoint = annotation.keypoints.add(id=keypoint_id, score=keypoint_score)
        keypoint.position.x, keypoint.position.y = point[0], point[1]
        if len(point) == 3:
            keypoint.position.z = point[2]
    return annotation

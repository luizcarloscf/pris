"""ArUco marker detection on an Image, with OpenCV."""

from __future__ import annotations

import cv2
from pris_msgs.image_pb2 import Image, ObjectAnnotations
from pris_msgs.utils.image import to_array

from pris_aruco_detector.conf.options_pb2 import (
    ArucoDictionary,
    CornerRefinement,
    DetectorOptions,
)


def dictionary_id(dictionary: int) -> int:
    """Return OpenCV's `cv2.aruco.DICT_*` value of an ArucoDictionary, which has the same names."""
    return int(getattr(cv2.aruco, ArucoDictionary.Name(dictionary)))


def corner_refinement_id(refinement: int) -> int:
    """Return OpenCV's `cv2.aruco.CORNER_REFINE_*` value of a CornerRefinement, same names."""
    return int(getattr(cv2.aruco, CornerRefinement.Name(refinement)))


class MarkerDetector(object):
    """Finds the markers of one dictionary in an image."""

    def __init__(self, options: DetectorOptions) -> None:
        """Create OpenCV's detector.

        Args:
            options: the dictionary and the corner refinement.
        """
        dictionary = cv2.aruco.getPredefinedDictionary(dictionary_id(options.dictionary))
        parameters = cv2.aruco.DetectorParameters()
        parameters.cornerRefinementMethod = corner_refinement_id(options.corner_refinement)
        self._detector = cv2.aruco.ArucoDetector(dictionary, parameters)

    def detect(self, image: Image) -> ObjectAnnotations:
        """Detect the markers of an image.

        Args:
            image: an encoded image.

        Returns:
            One annotation per marker, with its id, score 1 (ArUco has no confidence: a decoded
            marker passed its code check) and its 4 corners in pixels, in OpenCV's order:
            top-left, top-right, bottom-right, bottom-left.

        Raises:
            ValueError: the image's data can't be decoded.
            cv2.error: the image has no data, being empty or holding only a `uri`.
        """
        pixels = to_array(image, gray=True)
        corners, ids, _ = self._detector.detectMarkers(pixels)

        annotations = ObjectAnnotations()
        annotations.resolution.height, annotations.resolution.width = pixels.shape[:2]
        if ids is None:
            return annotations
        for marker_corners, marker_id in zip(corners, ids.flatten()):
            marker = annotations.objects.add(id=int(marker_id), label=str(marker_id), score=1.0)
            for x, y in marker_corners.reshape(4, 2):
                marker.region.vertices.add(x=float(x), y=float(y))
        return annotations

"""Multi-view marker localization, in NumPy and OpenCV.

A camera's `extrinsic` maps reference (world) coordinates to camera coordinates; a marker `pose`
maps marker coordinates to reference coordinates. Corners follow OpenCV's square-marker
convention: origin at the center, x right, y up, z out of the marker, in the order top-left,
top-right, bottom-right, bottom-left, the order pris-aruco-detector publishes.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace

import cv2
import numpy as np
import numpy.typing as npt
from pris_msgs.camera_pb2 import CameraCalibration
from pris_msgs.utils.tensor import to_array

Array = npt.NDArray[np.float64]


@dataclass(frozen=True)
class Camera:
    """A calibrated camera.

    Attributes:
        id: the camera id.
        intrinsic: 3x3 camera matrix, for images of `width` x `height` pixels.
        distortion: distortion coefficients, in OpenCV's order (k1, k2, p1, p2, k3, ...).
        extrinsic: 4x4, reference frame to camera frame.
        width: the calibration's image width.
        height: the calibration's image height.
    """

    id: int
    intrinsic: Array
    distortion: Array
    extrinsic: Array
    width: int
    height: int

    def scaled(self, width: int, height: int) -> Camera:
        """Return the same camera for images of another resolution, such as a binned stream.

        The intrinsic rows scale with the size.
        """
        if (width, height) == (self.width, self.height):
            return self
        intrinsic = self.intrinsic.copy()
        intrinsic[0] *= width / self.width
        intrinsic[1] *= height / self.height
        return replace(self, intrinsic=intrinsic, width=width, height=height)

    @property
    def focal(self) -> Array:
        """(fx, fy): turns normalized image errors into pixels."""
        return np.array([self.intrinsic[0, 0], self.intrinsic[1, 1]])


def camera_from_calibration(calibration: CameraCalibration, reference_frame: int) -> Camera:
    """Return the camera of a calibration, with its extrinsic from `reference_frame`.

    Raises:
        ValueError: the calibration has no extrinsic from `reference_frame`, matrices of the wrong
            shape, or no resolution.
    """
    for extrinsic in calibration.extrinsic:
        if extrinsic.source == reference_frame and extrinsic.target == calibration.id:
            break
    else:
        raise ValueError("camera {} has no extrinsic from frame {}".format(
            calibration.id, reference_frame))
    camera = Camera(
        id=calibration.id,
        intrinsic=to_array(calibration.intrinsic).astype(np.float64),
        distortion=to_array(calibration.distortion).astype(np.float64).ravel(),
        extrinsic=to_array(extrinsic.tf).astype(np.float64),
        width=calibration.resolution.width,
        height=calibration.resolution.height,
    )
    if camera.intrinsic.shape != (3, 3) or camera.extrinsic.shape != (4, 4):
        raise ValueError("camera {}: intrinsic {} and extrinsic {}, expected 3x3 and 4x4".format(
            camera.id, camera.intrinsic.shape, camera.extrinsic.shape))
    if camera.width <= 0 or camera.height <= 0:
        raise ValueError("camera {} has no calibration resolution".format(camera.id))
    return camera


def marker_corners(length: float) -> Array:
    """Return the 4x3 corners of a square marker of side `length`, in the marker frame."""
    half = length / 2.0
    return np.array([[-half, half, 0.0], [half, half, 0.0],
                     [half, -half, 0.0], [-half, -half, 0.0]])


def undistort(camera: Camera, pixels: npt.ArrayLike) -> Array:
    """Return the Nx2 normalized image coordinates (z = 1) of Nx2 pixel coordinates."""
    points = np.asarray(pixels, dtype=np.float64).reshape(-1, 1, 2)
    normalized = cv2.undistortPoints(points, camera.intrinsic, camera.distortion)
    return np.asarray(normalized, dtype=np.float64).reshape(-1, 2)


def transform(matrix: Array, points: Array) -> Array:
    """Return Nx3 points mapped by a 4x4 rigid transformation."""
    return np.asarray(points @ matrix[:3, :3].T + matrix[:3, 3], dtype=np.float64)


def invert(matrix: Array) -> Array:
    """Return the inverse of a 4x4 rigid transformation."""
    inverse = np.eye(4)
    inverse[:3, :3] = matrix[:3, :3].T
    inverse[:3, 3] = -matrix[:3, :3].T @ matrix[:3, 3]
    return inverse


def to_matrix(rotation_vector: npt.ArrayLike, translation: npt.ArrayLike) -> Array:
    """Return the 4x4 transformation of a Rodrigues rotation vector and a translation."""
    matrix = np.eye(4)
    matrix[:3, :3], _ = cv2.Rodrigues(np.asarray(rotation_vector, dtype=np.float64))
    matrix[:3, 3] = np.asarray(translation, dtype=np.float64).ravel()
    return matrix


def triangulate(extrinsics: Array, normalized: Array) -> Array:
    """Return Nx3 points seen by C cameras, by linear triangulation (DLT).

    Every point is solved at once: one batched SVD of N systems of 2C equations.

    Args:
        extrinsics: Cx4x4, reference to camera.
        normalized: CxNx2 normalized image coordinates.
    """
    projections = extrinsics[:, :3, :]
    x = normalized[:, :, 0:1]
    y = normalized[:, :, 1:2]
    rows_x = x * projections[:, None, 2, :] - projections[:, None, 0, :]
    rows_y = y * projections[:, None, 2, :] - projections[:, None, 1, :]
    systems = np.concatenate([rows_x, rows_y], axis=0).transpose(1, 0, 2)
    _, _, vt = np.linalg.svd(systems)
    homogeneous = vt[:, -1, :]
    return np.asarray(homogeneous[:, :3] / homogeneous[:, 3:], dtype=np.float64)


def kabsch(model: Array, points: Array) -> Array:
    """Return the 4x4 rigid transformation T minimizing |T(model) - points| (Kabsch).

    Always a proper rotation: a reflection, which the plain SVD solution can give for noisy or
    planar points, is corrected.
    """
    model_center = model.mean(axis=0)
    points_center = points.mean(axis=0)
    covariance = (model - model_center).T @ (points - points_center)
    u, _, vt = np.linalg.svd(covariance)
    sign = np.sign(np.linalg.det(vt.T @ u.T)) or 1.0
    rotation = vt.T @ np.diag([1.0, 1.0, sign]) @ u.T
    matrix = np.eye(4)
    matrix[:3, :3] = rotation
    matrix[:3, 3] = points_center - rotation @ model_center
    return matrix


def project(camera_extrinsic: Array, pose: Array, model: Array) -> Array:
    """Return the Nx2 normalized coordinates of the marker points `model` seen by a camera."""
    points = transform(camera_extrinsic @ pose, model)
    return points[:, :2] / points[:, 2:]


def residuals(pose: Array, cameras: Sequence[Camera], normalized: Array, model: Array) -> Array:
    """Return the CxNx2 reprojection errors in pixels: normalized error times focal length."""
    return np.stack([
        (project(camera.extrinsic, pose, model) - observed) * camera.focal
        for camera, observed in zip(cameras, normalized)
    ])


def camera_errors(pose: Array, cameras: Sequence[Camera], normalized: Array,
                  model: Array) -> Array:
    """Return the RMS reprojection error of each camera, in pixels."""
    errors = residuals(pose, cameras, normalized, model)
    return np.asarray(np.sqrt((errors ** 2).sum(axis=2).mean(axis=1)), dtype=np.float64)


def _cost(pose: Array, cameras: Sequence[Camera], normalized: Array, model: Array) -> float:
    if not _in_front(pose, cameras, model):
        return float("inf")
    return float((residuals(pose, cameras, normalized, model) ** 2).sum())


def _in_front(pose: Array, cameras: Sequence[Camera], model: Array) -> bool:
    return all((transform(camera.extrinsic @ pose, model)[:, 2] > 0).all() for camera in cameras)


def single_view_poses(camera: Camera, normalized: Array, model: Array) -> list[Array]:
    """Return the poses, up to two, that IPPE finds for a square marker seen by one camera.

    A small or distant marker has two plausible orientations, the planar flip; both are returned
    so that other cameras can tell them apart.
    """
    count, rotations, translations, _ = cv2.solvePnPGeneric(
        model, normalized.reshape(-1, 1, 2), np.eye(3), np.zeros(5),
        flags=cv2.SOLVEPNP_IPPE_SQUARE)
    camera_to_reference = invert(camera.extrinsic)
    return [camera_to_reference @ to_matrix(rotations[i], translations[i])
            for i in range(count)]


def initial_poses(cameras: Sequence[Camera], normalized: Array, model: Array) -> list[Array]:
    """Return the candidate poses: triangulation and Kabsch with two or more cameras, and the IPPE
    poses of each camera alone."""
    candidates = []
    if len(cameras) >= 2:
        extrinsics = np.stack([camera.extrinsic for camera in cameras])
        points = triangulate(extrinsics, normalized)
        if np.isfinite(points).all():
            candidates.append(kabsch(model, points))
    for camera, observed in zip(cameras, normalized):
        candidates.extend(single_view_poses(camera, observed, model))
    return candidates


def _exp(delta: Array) -> Array:
    return to_matrix(delta[:3], delta[3:])


def refine(pose: Array, cameras: Sequence[Camera], normalized: Array, model: Array,
           iterations: int = 30) -> Array:
    """Refine a pose with Levenberg-Marquardt, minimizing the reprojection error of every point.

    The pose is updated in the marker frame (pose @ exp(delta)), whose origin is the marker's
    center, which keeps rotation and translation decoupled.
    """
    step = 1e-6
    damping = 1e-3
    cost = _cost(pose, cameras, normalized, model)
    for _ in range(iterations):
        error = residuals(pose, cameras, normalized, model).ravel()
        jacobian = np.empty((error.size, 6))
        for i in range(6):
            delta = np.zeros(6)
            delta[i] = step
            forward = residuals(pose @ _exp(delta), cameras, normalized, model).ravel()
            backward = residuals(pose @ _exp(-delta), cameras, normalized, model).ravel()
            jacobian[:, i] = (forward - backward) / (2 * step)
        hessian = jacobian.T @ jacobian
        gradient = jacobian.T @ error
        while True:
            try:
                delta = np.linalg.solve(hessian + damping * np.diag(np.diag(hessian) + 1e-12),
                                        -gradient)
            except np.linalg.LinAlgError:
                return pose
            candidate = pose @ _exp(delta)
            candidate_cost = _cost(candidate, cameras, normalized, model)
            if candidate_cost < cost:
                improvement = cost - candidate_cost
                pose, cost = candidate, candidate_cost
                damping = max(damping / 10, 1e-9)
                break
            damping *= 10
            if damping > 1e9:
                return pose
        if improvement <= 1e-12 * max(cost, 1e-12) or np.abs(delta).max() < 1e-12:
            break
    return pose


@dataclass(frozen=True)
class Observation:
    """A marker seen by one camera.

    Attributes:
        camera: the camera.
        corners: 4x2 corner pixels, in the order of `marker_corners`.
    """

    camera: Camera
    corners: Array


@dataclass(frozen=True)
class Estimate:
    """A marker's pose.

    Attributes:
        pose: 4x4, marker frame to reference frame.
        error: the RMS reprojection error over the cameras used, in pixels.
        camera_errors: the RMS reprojection error of each camera used, in pixels.
        rejected: the cameras dropped as outliers.
    """

    pose: Array
    error: float
    camera_errors: dict[int, float]
    rejected: tuple[int, ...] = field(default_factory=tuple)

    @property
    def camera_ids(self) -> tuple[int, ...]:
        """The cameras used."""
        return tuple(self.camera_errors)


def localize(observations: Sequence[Observation], length: float,
             max_camera_error: float) -> Estimate | None:
    """Estimate the pose of a marker of side `length` from its corners in one or more cameras.

    Candidates from triangulation and from each camera alone are scored by their reprojection
    error over all cameras; the best one is refined. While more than one camera is left and the
    worst one is off by more than `max_camera_error` pixels (RMS), it is dropped and the pose
    recomputed.

    Returns:
        The estimate, or None without observations or when no candidate is in front of every
        camera.
    """
    model = marker_corners(length)
    cameras = [observation.camera for observation in observations]
    normalized = [undistort(o.camera, o.corners) for o in observations]
    rejected: list[int] = []
    while cameras:
        stacked = np.stack(normalized)
        candidates = initial_poses(cameras, stacked, model)
        costs = [_cost(pose, cameras, stacked, model) for pose in candidates]
        if not candidates or not np.isfinite(min(costs)):
            return None
        pose = refine(candidates[int(np.argmin(costs))], cameras, stacked, model)
        errors = camera_errors(pose, cameras, stacked, model)
        worst = int(np.argmax(errors))
        if len(cameras) > 1 and errors[worst] > max_camera_error:
            rejected.append(cameras[worst].id)
            del cameras[worst], normalized[worst]
            continue
        total = float(np.sqrt((errors ** 2).mean()))
        return Estimate(
            pose=pose,
            error=total,
            camera_errors={camera.id: float(e) for camera, e in zip(cameras, errors)},
            rejected=tuple(rejected),
        )
    return None
